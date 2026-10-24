#!/usr/bin/env python3
"""WI-05: inventory static configuration names without exporting any values.

Standard library only. Never imports Kala, reads environment/example files,
evaluates Terraform/Make, or contacts services. Unknown syntax is reported and
causes --check to fail. This is a source catalogue, not proof of deployed state.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import json
from pathlib import Path
import re
import sys

ENV_NAME = re.compile(r"[A-Z][A-Z0-9_]*\Z")
JS_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mts", ".cts", ".mjs", ".cjs"}
CONFIGS = {label: f"services/{label}/app/config.py" for label in ("api", "worker")}
HCL_NO_CODE = re.compile(r'"(?:\\.|[^"\\])*"|/\*[\s\S]*?\*/|//[^\n]*|#[^\n]*')


class InventoryError(Exception):
    """A safe, value-free diagnostic suitable for stdout/stderr."""


def _blank(text: str) -> str:
    return "".join("\n" if c == "\n" else " " for c in text)


def _line(source: str, offset: int) -> int:
    return source.count("\n", 0, offset) + 1


def read_source(root: Path, relative: str) -> str:
    """Allowlist first, before opening anything; refuse symlinks at any level."""
    rel = Path(relative)
    permitted = relative in {*CONFIGS.values(), "Makefile"}
    permitted |= relative.startswith(("apps/web/src/", "supabase/functions/")) and rel.suffix in JS_SUFFIXES
    permitted |= relative.startswith("infra/terraform/") and rel.suffix == ".tf"
    if not permitted or rel.is_absolute() or ".." in rel.parts or any(p.startswith(".env") for p in rel.parts):
        raise InventoryError("Refused source outside the static-source allowlist")
    candidate = root / rel
    if any((root / Path(*rel.parts[:i])).is_symlink() for i in range(1, len(rel.parts) + 1)):
        raise InventoryError(f"Refused symlink source: {relative}")
    if root not in candidate.resolve().parents:
        raise InventoryError("Refused source outside the repository")
    try:
        return candidate.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise InventoryError(f"Could not read static source: {relative}") from None


def classify_default(name: str, value: object, *, literal: bool = True, sensitive: bool = False) -> tuple[str, str]:
    """Conservative publication review; never return or format the input value."""
    if not literal:
        return "unknown", "Computed expression; not evaluated"
    if value is None or value == "":
        return "yes", "Empty sentinel; runtime usability is separate"
    credential = re.search(r"SECRET|PRIVATE_KEY|API_KEY|SERVICE_KEY", name.upper())
    if sensitive or credential:
        return "no", "Nonempty credential-like or sensitive default; never publish"
    if isinstance(value, (bool, int, float)):
        return "yes", "Nonsecret scalar"
    if name in {"AWS_REGION", "region"} and isinstance(value, str) and re.fullmatch(r"[a-z]+-[a-z]+-\d+", value):
        return "yes", "Region identifier"
    if name == "FRONTEND_URL" and isinstance(value, str) and re.fullmatch(r"https?://(?:localhost|127\.0\.0\.1)(?::\d+)?/?", value):
        return "yes", "Loopback development URL"
    return "unknown", "Nonempty string or composite needs publication review; value omitted"


def _js_code_mask(source: str) -> str:
    """Mask strings/comments, while retaining code inside template expressions.

    This is a reference scanner, not a TS parser. Regex literals containing an
    environment-access spelling may be conservatively reported as references.
    """
    chars = list(source)
    size = len(source)

    def hide(start: int, end: int) -> None:
        chars[start:end] = _blank(source[start:end])

    def template(pos: int) -> int:
        hide(pos, pos + 1)
        pos += 1
        while pos < size:
            if source[pos] == "\\":
                hide(pos, min(size, pos + 2)); pos += 2
            elif source[pos] == "`":
                hide(pos, pos + 1); return pos + 1
            elif source.startswith("${", pos):
                hide(pos, pos + 2); pos = code(pos + 2, True)
            else:
                hide(pos, pos + 1); pos += 1
        return pos

    def code(pos: int, expression: bool = False) -> int:
        depth = 0
        while pos < size:
            c = source[pos]
            if source.startswith("//", pos):
                end = source.find("\n", pos)
                end = size if end < 0 else end
                hide(pos, end); pos = end
            elif source.startswith("/*", pos):
                end = source.find("*/", pos + 2)
                end = size if end < 0 else end + 2
                hide(pos, end); pos = end
            elif c in "\"'":
                start, quote = pos, c
                pos += 1
                while pos < size:
                    if source[pos] == "\\": pos += 2
                    elif source[pos] == quote: pos += 1; break
                    else: pos += 1
                hide(start, min(size, pos))
            elif c == "`": pos = template(pos)
            elif c == "{" and expression: depth += 1; pos += 1
            elif c == "}" and expression:
                if depth == 0:
                    hide(pos, pos + 1); return pos + 1
                depth -= 1; pos += 1
            else: pos += 1
        return pos

    code(0)
    return "".join(chars)


def _hcl_mask(source: str) -> str:
    return HCL_NO_CODE.sub(lambda m: _blank(m[0]), source)


def _block_end(mask: str, start: int) -> int:
    depth = 0
    for i in range(start, len(mask)):
        if mask[i] == "{": depth += 1
        elif mask[i] == "}":
            depth -= 1
            if depth == 0: return i
    raise InventoryError("Unbalanced Terraform block; source content omitted")


def _hcl_attrs(source: str, mask: str, start: int, end: int) -> dict[str, tuple[str, int]]:
    """Read top-level assignments only; retain offsets, never evaluate HCL."""
    body, code = source[start:end], mask[start:end]
    depths, depth = [], 0
    for c in code:
        depths.append(depth)
        if c in "{[(":  # object, list and parenthesized expression
            depth += 1
        elif c in "}])": depth -= 1
    matches = []
    for m in re.finditer(r'(?<![\w.])([A-Za-z_][\w-]*|"(?:\\.|[^"\\])*")\s*=(?!=|>)', body):
        if depths[m.start()] == 0 and code[m.end() - 1] == "=":
            matches.append(m)
    result = {}
    for i, m in enumerate(matches):
        key = json.loads(m[1]) if m[1].startswith('"') else m[1]
        stop = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        result[key] = (body[m.end():stop].strip(), start + m.start())
    return result


def _hcl_literal(expression: str) -> tuple[object, bool]:
    # Remove comments but preserve quoted strings. Heredocs/composites stay unknown.
    expression = HCL_NO_CODE.sub(lambda m: m[0] if m[0].startswith('"') else _blank(m[0]), expression).strip()
    try:
        value = json.loads(expression)
        if isinstance(value, str) and ("${" in value or "%{" in value): return None, False
        return value, True
    except (ValueError, TypeError):
        return None, False


class Collector:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.rows: dict[tuple[str, str], dict] = {}
        self.fields: dict[str, dict] = {}
        self.issues: list[dict] = []
        self.sources: list[str] = []
        self.lambda_environment: list[dict] = []

    def read(self, path: str) -> str:
        source = read_source(self.root, path)
        self.sources.append(path)
        return source

    def issue(self, source: str, message: str) -> None:
        self.issues.append({"source": source, "issue": message})

    def add(self, name: str, consumer: str, source: str, *, default: bool = False,
            safety: str = "unknown", reason: str = "No source fallback", namespace: str = "runtime") -> None:
        if not re.fullmatch(r"[A-Za-z_][\w-]*", name):
            self.issue(source, "Unsupported configuration name; content omitted")
            return
        row = self.rows.setdefault((namespace, name), {"namespace": namespace, "name": name,
            "consumers": [], "sources": [], "has_default": "no", "default_safe_to_publish": "unknown", "reasons": []})
        for column, item in (("consumers", consumer), ("sources", source), ("reasons", reason)):
            if item not in row[column]: row[column].append(item)
        if default:
            previous = row["default_safe_to_publish"] if row["has_default"] == "yes" else safety
            row["has_default"] = "yes"
            row["default_safe_to_publish"] = max((previous, safety), key={"yes": 0, "unknown": 1, "no": 2}.__getitem__)

    def python_config(self, label: str, path: str) -> None:
        source = self.read(path)
        try: tree = ast.parse(source)
        except SyntaxError as exc:
            raise InventoryError(f"Invalid Python source: {path}:{exc.lineno}; content omitted") from None
        fields = self.fields[label] = {}
        settings = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Settings"]
        if len(settings) != 1:
            self.issue(path, "Expected one Settings class")
        for cls in settings:
            for node in cls.body:
                if not isinstance(node, ast.AnnAssign) or not isinstance(node.target, ast.Name): continue
                ref = f"{path}:{node.lineno}"
                call = node.value
                if not isinstance(call, ast.Call) or ast.unparse(call.func) != "Field":
                    self.issue(ref, "Unsupported settings declaration; content omitted"); continue
                kw = {k.arg: k.value for k in call.keywords}
                alias = kw.get("validation_alias", kw.get("alias"))
                if not isinstance(alias, ast.Constant) or not isinstance(alias.value, str) or not ENV_NAME.fullmatch(alias.value):
                    self.issue(ref, "Nonliteral or unsupported environment alias; membership unknown"); continue
                default = kw.get("default", call.args[0] if call.args else None)
                has_default = "default_factory" in kw or (default is not None and not (isinstance(default, ast.Constant) and default.value is Ellipsis))
                try: value, literal = ast.literal_eval(default), True
                except (ValueError, TypeError): value, literal = None, False
                if "default_factory" in kw: value, literal = None, False
                safety, reason = classify_default(alias.value, value, literal=literal)
                self.add(alias.value, label, ref, default=has_default, safety=safety,
                         reason=reason if has_default else "Required field; no source default")
                fields[node.target.id] = {"alias": alias.value, "source": ref,
                    "default": ast.dump(default) if default is not None else None,
                    "default_factory": ast.dump(kw["default_factory"]) if "default_factory" in kw else None}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or ast.unparse(node.func) not in {"os.getenv", "os.environ.get"}: continue
            ref = f"{path}:{node.lineno}"
            if not node.args or not isinstance(node.args[0], ast.Constant) or not isinstance(node.args[0].value, str) or not ENV_NAME.fullmatch(node.args[0].value):
                self.issue(ref, "Dynamic bootstrap environment name; membership unknown"); continue
            default = node.args[1] if len(node.args) > 1 else next((k.value for k in node.keywords if k.arg == "default"), None)
            try: value, literal = ast.literal_eval(default), True
            except (ValueError, TypeError): value, literal = None, False
            safety, reason = classify_default(node.args[0].value, value, literal=literal)
            self.add(node.args[0].value, label + " bootstrap", ref, default=default is not None,
                     safety=safety, reason="Bootstrap read before secret payload loading" + ("; " + reason if default is not None else ""))

    def javascript(self, base: str, consumer: str) -> None:
        marker = r"import\s*\.\s*meta\s*\.\s*env" if consumer == "web" else r"Deno\s*\.\s*env\s*\.\s*get"
        suffix = r"\s*(?:\.\s*([A-Za-z_]\w*)|\[\s*['\"]([A-Za-z_]\w*)['\"]\s*\])" if consumer == "web" else r"\s*\(\s*['\"]([A-Za-z_]\w*)['\"]\s*\)"
        for p in sorted((self.root / base).rglob("*")):
            if not p.is_file() or p.suffix not in JS_SUFFIXES: continue
            path = p.relative_to(self.root).as_posix()
            source = self.read(path); mask = _js_code_mask(source)
            matched = set()
            for m in re.finditer(marker + suffix, source):
                if not mask[m.start():m.start()+1].strip(): continue
                name = next(g for g in m.groups() if g)
                matched.add(m.start())
                fallback = bool(re.match(r"\s*!?\s*(?:\|\||\?\?)", source[m.end():]))
                builtin = consumer == "web" and name in {"DEV", "PROD", "MODE", "BASE_URL", "SSR"}
                self.add(name, "web Vite built-in" if builtin else consumer, f"{path}:{_line(source,m.start())}",
                         default=fallback, reason="Fallback expression; value omitted" if fallback else
                         "Vite-provided built-in; no source default" if builtin else "No source fallback")
            for m in re.finditer(marker, mask):
                if m.start() not in matched:
                    self.issue(f"{path}:{_line(source,m.start())}", "Dynamic or unsupported environment access; membership unknown")

    def terraform(self) -> None:
        for p in sorted((self.root / "infra/terraform").glob("*.tf")):
            path = p.relative_to(self.root).as_posix()
            source = self.read(path); mask = _hcl_mask(source)
            if "<<" in mask:
                self.issue(path, "Terraform heredoc unsupported; inspect names manually")
            for m in re.finditer(r'\bvariable\s+"([\w-]+)"\s*\{', source):
                if mask[m.start():m.start()+8] != "variable": continue
                start = source.index("{", m.start()); end = _block_end(mask, start)
                attrs = _hcl_attrs(source, mask, start + 1, end)
                default = attrs.get("default")
                value, literal = _hcl_literal(default[0]) if default else (None, False)
                sensitive = _hcl_literal(attrs.get("sensitive", ("false",0))[0])[0] is True
                safety, reason = classify_default(m[1], value, literal=literal, sensitive=sensitive)
                self.add(m[1], "Terraform input", f"{path}:{_line(source,m.start())}", namespace="terraform",
                         default=default is not None, safety=safety, reason=reason if default else "No Terraform default")
            for m in re.finditer(r'\bresource\s+"aws_lambda_function"\s+"([\w-]+)"\s*\{', source):
                if mask[m.start():m.start()+8] != "resource": continue
                start = source.index("{", m.start()); end = _block_end(mask, start)
                for env in re.finditer(r"\benvironment\s*\{", mask[start:end]):
                    es = start + env.end()-1; ee = _block_end(mask, es)
                    attrs = _hcl_attrs(source,mask,es+1,ee)
                    variables = attrs.get("variables")
                    if not variables or not variables[0].startswith("{"):
                        self.issue(f"{path}:{_line(source,es)}", "Nonliteral Lambda environment map; membership unknown"); continue
                    vs = source.index("{", variables[1]); ve = _block_end(mask,vs)
                    for name, (_,pos) in _hcl_attrs(source,mask,vs+1,ve).items():
                        if not ENV_NAME.fullmatch(name):
                            self.issue(f"{path}:{_line(source,pos)}", "Unsupported Lambda environment key; membership unknown"); continue
                        ref = f"{path}:{_line(source,pos)}"
                        self.lambda_environment.append({"lambda":m[1],"name":name,"source":ref})
                        self.add(name,f"Terraform Lambda {m[1]}",ref,reason="Explicit Lambda assignment; expression not exported")

    def makefile(self) -> None:
        for i,line in enumerate(self.read("Makefile").splitlines(),1):
            if line.startswith("\t"): continue
            m = re.match(r"\s*(?:export\s+)?([A-Za-z_]\w*)\s*([?:+!]?=)\s*(.*)",line)
            if not m: continue
            rhs = m[3].split("#",1)[0].strip()
            if "$" in rhs or m[2] == "!=": safety,reason = "unknown","Computed Make expression; never executed"
            elif m[1] in {"AWS","TF"} and re.fullmatch(r"(?:pnpm\s+)?(?:aws|terraform)",rhs):
                safety,reason = "yes","Static tool selector"
            else: safety,reason = classify_default("AWS_REGION" if m[1] == "REGION" else m[1],rhs)
            self.add(m[1],"Makefile",f"Makefile:{i}",namespace="make",default=True,safety=safety,
                     reason=reason+("; conditional assignment" if m[2] == "?=" else "; defined expression"))

    def collect(self) -> dict:
        for label,path in CONFIGS.items(): self.python_config(label,path)
        self.javascript("apps/web/src","web")
        self.javascript("supabase/functions","edge")
        self.terraform()
        self.makefile()
        duplicates = []
        for field in sorted(self.fields["api"].keys() & self.fields["worker"].keys()):
            a,w = self.fields["api"][field],self.fields["worker"][field]
            duplicates.append({"field":field,"api_alias":a["alias"],"worker_alias":w["alias"],
                "alias_exact_match":a["alias"]==w["alias"],
                "default_exact_match":(a["default"],a["default_factory"])==(w["default"],w["default_factory"]),
                "api_source":a["source"],"worker_source":w["source"]})
        rows = sorted(self.rows.values(),key=lambda r:(r["namespace"],r["name"]))
        overlaps = sorted({v["name"] for v in self.lambda_environment if any(v["name"]==f["alias"] for fields in self.fields.values() for f in fields.values())})
        return {"inventory":rows,"duplicates":duplicates,"lambda_environment":self.lambda_environment,
            "conditional_shadow_names":overlaps,"actual_secret_payload_membership":"unknown","issues":self.issues,
            "source_files":self.sources,"summary":{"rows":len(rows),"api_fields":len(self.fields["api"]),
            "worker_fields":len(self.fields["worker"]),"duplicate_fields":len(duplicates),
            "namespace_counts":dict(Counter(r["namespace"] for r in rows)),
            "default_safety_counts":dict(Counter(r["default_safe_to_publish"] for r in rows)),
            "has_default_counts":dict(Counter(r["has_default"] for r in rows))}}


def markdown(report: dict) -> str:
    lines = ["| Namespace | Name | Consumers | Has default | Default safe to publish | Source | Classification reason |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for row in report["inventory"]:
        cells=[row["namespace"],row["name"],", ".join(row["consumers"]),row["has_default"],
               row["default_safe_to_publish"],", ".join(row["sources"]),"; ".join(row["reasons"])]
        lines.append("| "+" | ".join(cells)+" |")
    lines += ["", "API/worker duplicates (defaults omitted):", "",
              "| Field | API alias | Worker alias | Alias matches | Default matches | API source | Worker source |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    for d in report["duplicates"]:
        lines.append("| "+" | ".join([d["field"],d["api_alias"],d["worker_alias"],
            "yes" if d["alias_exact_match"] else "no","yes" if d["default_exact_match"] else "no",d["api_source"],d["worker_source"]])+" |")
    lines += ["", "Conditional shadow names: "+(", ".join(report["conditional_shadow_names"]) or "none"),
              "Actual secret payload membership: unknown."]
    for issue in report["issues"]: lines.append(issue["source"]+": "+issue["issue"])
    return "\n".join(lines)+"\n"


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument("--format",choices=("markdown","json"),default="markdown")
    parser.add_argument("--check",action="store_true",help="Fail on unsupported syntax or duplicated-setting drift")
    args=parser.parse_args(argv)
    try: report=Collector(args.root).collect()
    except InventoryError as exc:
        print(str(exc),file=sys.stderr)
        return 1
    print(json.dumps(report,indent=2) if args.format=="json" else markdown(report),end="\n" if args.format=="json" else "")
    drift=any(not d["alias_exact_match"] or not d["default_exact_match"] for d in report["duplicates"])
    return int(args.check and (bool(report["issues"]) or drift))


if __name__=="__main__":
    raise SystemExit(main())
