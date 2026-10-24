"""WI-05 regression tests: source-only inventory, redaction and complete examples."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import config_inventory as inventory


class ConfigInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="kala-inventory-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for label in ("api", "worker"):
            self.write(f"services/{label}/app/config.py", "class Settings:\n    pass\n")
        self.write("Makefile", "")

    def write(self, relative, contents):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)
        return path

    def collect(self):
        return inventory.Collector(self.root).collect()

    def row(self, report, name, namespace="runtime"):
        return next(r for r in report["inventory"] if (r["namespace"], r["name"]) == (namespace, name))

    def test_WI_05_defaults_and_factories_never_export_values(self):
        self.write("services/api/app/config.py", '''class Settings:
    key: str = Field(default="DO_NOT_EXPORT_CREDENTIAL", alias="DEMO_API_KEY")
    count: int = Field(default=3, alias="COUNT")
    required: str = Field(..., alias="REQUIRED")
    generated: str = Field(default_factory=generate, alias="GENERATED")
''')
        report = self.collect()
        for output in (json.dumps(report), inventory.markdown(report)):
            self.assertNotIn("DO_NOT_EXPORT_CREDENTIAL", output)
            self.assertNotIn("generate", output)
            self.assertNotIn("default_value", output)
        self.assertEqual(self.row(report, "DEMO_API_KEY")["default_safe_to_publish"], "no")
        self.assertEqual(self.row(report, "COUNT")["default_safe_to_publish"], "yes")
        self.assertEqual(self.row(report, "REQUIRED")["has_default"], "no")
        self.assertEqual(self.row(report, "GENERATED")["has_default"], "yes")
        self.assertEqual(self.row(report, "GENERATED")["default_safe_to_publish"], "unknown")

    def test_WI_05_duplicate_alias_default_and_factory_drift_is_reported(self):
        self.write("services/api/app/config.py", '''class Settings:
    first: str = Field(default="HIDDEN_FIRST", alias="FIRST")
    second: str = Field(default_factory=make_one, alias="SECOND")
''')
        self.write("services/worker/app/config.py", '''class Settings:
    first: str = Field(default="HIDDEN_SECOND", alias="RENAMED_FIRST")
    second: str = Field(default_factory=make_two, alias="SECOND")
''')
        report = self.collect()
        self.assertFalse(report["duplicates"][0]["alias_exact_match"])
        self.assertTrue(all(not d["default_exact_match"] for d in report["duplicates"]))
        self.assertNotIn("HIDDEN_", json.dumps(report))
        with redirect_stdout(io.StringIO()):
            self.assertEqual(inventory.main(["--root", str(self.root), "--check"]), 1)

    def test_WI_05_js_comments_strings_templates_and_fallbacks(self):
        self.write("apps/web/src/demo.ts", '''
// import.meta.env.FALSE_COMMENT
/* import.meta.env.FALSE_BLOCK */
const a = "import.meta.env.FALSE_STRING";
const b = import.meta.env["VITE_BRACKET"] ?? "HIDDEN_FALLBACK";
const c = `text import.meta.env.FALSE_TEMPLATE ${import.meta.env.VITE_TEMPLATE}`;
const d = import.meta.env.DEV;
''')
        self.write("supabase/functions/demo/index.ts", '''
// Deno.env.get("FALSE_EDGE")
const endpoint = Deno.env.get("EDGE_ENDPOINT");
const token = Deno.env.get("EDGE_SECRET") ?? "HIDDEN_EDGE_FALLBACK";
''')
        report = self.collect()
        self.assertEqual({r["name"] for r in report["inventory"]},
                         {"VITE_BRACKET", "VITE_TEMPLATE", "DEV", "EDGE_ENDPOINT", "EDGE_SECRET"})
        self.assertEqual(self.row(report, "VITE_BRACKET")["has_default"], "yes")
        self.assertEqual(self.row(report, "EDGE_SECRET")["default_safe_to_publish"], "unknown")
        self.assertNotIn("HIDDEN_", json.dumps(report))
        self.assertFalse(report["issues"])

    def test_WI_05_dynamic_js_and_python_aliases_fail_check_without_exporting_expressions(self):
        self.write("apps/web/src/demo.ts", 'const x = import.meta.env[HIDDEN_EXPRESSION];\n')
        self.write("supabase/functions/demo/index.ts", 'const x = Deno.env.get(HIDDEN_EXPRESSION);\n')
        self.write("services/api/app/config.py", 'class Settings:\n    x: str = Field(default="", alias=HIDDEN_ALIAS)\n')
        report = self.collect()
        self.assertEqual(len(report["issues"]), 3)
        self.assertNotIn("HIDDEN_", json.dumps(report))
        with redirect_stdout(io.StringIO()):
            self.assertEqual(inventory.main(["--root", str(self.root), "--check"]), 1)

    def test_WI_05_terraform_quoted_keys_nested_braces_and_sensitive_defaults(self):
        self.write("services/api/app/config.py", 'class Settings:\n    url: str = Field(default="", alias="FRONTEND_URL")\n')
        self.write("infra/terraform/demo.tf", '''
# variable "FALSE_COMMENT" { default = "hidden" }
variable "region" { type = string default = "ap-southeast-1" }
variable "sensitive_input" { sensitive = true default = "HIDDEN_TF_DEFAULT" }
variable "required_input" { type = string }
resource "aws_lambda_function" "demo" {
  description = "braces { } and FRONTEND_URL = ignored"
  environment { variables = {
    "FRONTEND_URL" = var.frontend
    EXTRA_NAME = "HIDDEN_ENV_VALUE ${var.region}"
  } }
}
''')
        report = self.collect()
        self.assertEqual(self.row(report, "region", "terraform")["has_default"], "yes")
        self.assertEqual(self.row(report, "required_input", "terraform")["has_default"], "no")
        self.assertEqual(self.row(report, "sensitive_input", "terraform")["default_safe_to_publish"], "no")
        self.assertEqual(report["conditional_shadow_names"], ["FRONTEND_URL"])
        self.assertEqual(report["actual_secret_payload_membership"], "unknown")
        self.assertEqual({e["name"] for e in report["lambda_environment"]}, {"FRONTEND_URL", "EXTRA_NAME"})
        self.assertNotIn("HIDDEN_", json.dumps(report))
        self.assertFalse(report["issues"])

    def test_WI_05_dynamic_terraform_map_reports_unknown(self):
        self.write("infra/terraform/demo.tf", '''resource "aws_lambda_function" "demo" {
  environment { variables = merge(var.HIDDEN_MAP, {}) }
}''')
        report = self.collect()
        self.assertEqual(len(report["issues"]), 1)
        self.assertNotIn("HIDDEN_MAP", json.dumps(report))

    def test_WI_05_make_expressions_are_never_executed_or_exported(self):
        self.write("Makefile", '''REGION ?= ap-southeast-1
ACCOUNT ?= $(shell HIDDEN_COMMAND)
ECR = $(ACCOUNT).HIDDEN_HOST
TARGET != HIDDEN_COMMAND
demo:
\tHIDDEN_RECIPE=HIDDEN_VALUE command
''')
        report = self.collect()
        self.assertEqual({r["name"] for r in report["inventory"]}, {"REGION", "ACCOUNT", "ECR", "TARGET"})
        self.assertEqual(self.row(report, "ACCOUNT", "make")["default_safe_to_publish"], "unknown")
        self.assertNotIn("HIDDEN_", json.dumps(report))

    def test_WI_05_forbidden_paths_rejected_before_any_open(self):
        with patch.object(Path, "read_text", side_effect=AssertionError("File must not be opened")):
            for forbidden in (".env", "services/api/.env", "apps/web/.env.local", "services/api/.env.example",
                              "secret.json", "infra/terraform/terraform.tfvars", "infra/terraform/terraform.tfstate",
                              "../services/api/app/config.py"):
                with self.subTest(forbidden=forbidden), self.assertRaises(inventory.InventoryError):
                    inventory.read_source(self.root, forbidden)

    def test_WI_05_symlink_sources_rejected(self):
        target = self.write("not-a-source.txt", "UNREAD_FIXTURE")
        linked = self.root / "apps/web/src/linked.ts"
        linked.parent.mkdir(parents=True)
        linked.symlink_to(target)
        with patch.object(Path, "read_text", side_effect=AssertionError("Symlink must not be opened")):
            with self.assertRaises(inventory.InventoryError):
                inventory.read_source(self.root, "apps/web/src/linked.ts")

    def test_WI_05_invalid_python_diagnostic_never_echoes_source(self):
        self.write("services/api/app/config.py", 'HIDDEN_INVALID_SOURCE = "unterminated\n')
        stream = io.StringIO()
        with redirect_stderr(stream):
            self.assertEqual(inventory.main(["--root", str(self.root)]), 1)
        self.assertNotIn("HIDDEN_INVALID_SOURCE", stream.getvalue())
        self.assertIn("content omitted", stream.getvalue())

    def test_WI_05_repository_documents_and_examples_cover_every_declared_name(self):
        root = Path(__file__).resolve().parents[1]
        report = inventory.Collector(root).collect()
        self.assertFalse(report["issues"])
        self.assertEqual(report["summary"]["rows"], 67)
        self.assertEqual(report["summary"]["api_fields"], 43)
        self.assertEqual(report["summary"]["worker_fields"], 25)
        self.assertEqual(len(report["duplicates"]), 21)
        self.assertTrue(all(d["alias_exact_match"] and d["default_exact_match"] for d in report["duplicates"]))
        self.assertEqual(report["conditional_shadow_names"], ["FRONTEND_URL", "WORKER_FUNCTION_ARN"])
        self.assertTrue(all(not any(part.startswith(".env") for part in Path(p).parts) for p in report["source_files"]))
        for label, expected in (("api", 44), ("worker", 26), ("web", 3)):
            path = f"services/{label}/.env.example" if label != "web" else "apps/web/.env.example"
            # Explicit Lane C grant: examples only; never actual dotenv files.
            text = (root / path).read_text()
            names = re.findall(r"^# ([A-Z][A-Z0-9_]*)=<[A-Z_]+>$", text, re.M)
            wanted = {r["name"] for r in report["inventory"] if r["namespace"] == "runtime" and
                      ((label == "web" and r["name"].startswith("VITE_")) or
                       (label != "web" and (label in r["consumers"] or label + " bootstrap" in r["consumers"])))}
            self.assertEqual(len(names), expected)
            self.assertEqual(set(names), wanted)
            self.assertEqual(len(names), len(set(names)))
            self.assertTrue(all(not line or line.startswith("#") for line in text.splitlines()))
        doc = (root / "docs/engineering/secrets.md").read_text()
        sections = {
            "backend": ("## Backend secrets and settings", "## Bootstrap settings"),
            "bootstrap": ("## Bootstrap settings", "## Browser config"),
            "browser": ("## Browser config", "## Edge Function config"),
            "edge": ("## Edge Function config", "## Terraform input catalogue"),
            "terraform": ("## Terraform input catalogue", "## Makefile configuration catalogue"),
            "make": ("## Makefile configuration catalogue", "## Accounts"),
        }
        expected_sets = {
            "backend": {r["name"] for r in report["inventory"] if any(c in ("api", "worker") for c in r["consumers"])},
            "bootstrap": {"KALA_SECRETS_ARN"},
            "browser": {r["name"] for r in report["inventory"] if any(c.startswith("web") for c in r["consumers"])},
            "edge": {r["name"] for r in report["inventory"] if "edge" in r["consumers"]},
            "terraform": {r["name"] for r in report["inventory"] if r["namespace"] == "terraform"},
            "make": {r["name"] for r in report["inventory"] if r["namespace"] == "make"},
        }
        for section, (start, end) in sections.items():
            text = doc.split(start, 1)[1].split(end, 1)[0]
            actual = re.findall(r"^\| `([A-Za-z_][A-Za-z0-9_]*)` \|", text, re.M)
            self.assertEqual(set(actual), expected_sets[section], section)
            self.assertEqual(len(actual), len(set(actual)), section)
        backend = doc.split(sections["backend"][0], 1)[1].split(sections["backend"][1], 1)[0]
        for name, consumers in re.findall(r"^\| `([A-Z][A-Z0-9_]*)` \| [^|]+ \| ([^|]+) \|", backend, re.M):
            wanted = {c for c in self.row(report, name)["consumers"] if c in ("api", "worker")}
            self.assertEqual(set(consumers.strip().split(", ")), wanted, name)


if __name__ == "__main__":
    unittest.main()
