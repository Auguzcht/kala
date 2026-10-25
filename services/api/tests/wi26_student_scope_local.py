"""AUTH-REQ-007 strict scope proof. Run with API uv Python (3.12+).

cd services/api && uv run python tests/wi26_student_scope_local.py
"""
import argparse
import ast
import copy
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = "38f6c75dbf025097bb5b09b45def24bc497450bd"
ROUTES = {
    "courses": {"get_course", "memory_summary"},
    "twin": {"get_twin", "next_up", "learning_plan"},
    "diagnostic": {"get_content", "list_modules", "get_diagnostic_status", "get_diagnostic"},
    "flashcards": {"skill_cards", "deck"},
    "gamification": {"summary"},
    "practice": {"next_item", "list_sets", "get_set", "get_set_results"},
    "lessons": {"get_lesson"},
    "tutor": {"list_conversations", "get_conversation"},
}
IMPORT = ast.parse("from app.routers import bank as bank_router").body[0]


def dump(node):
    return ast.dump(node, include_attributes=False)


def guard(module, name):
    course = 'convo["course_id"]' if name == "get_conversation" else "course_id"
    local_import = "    from app.routers import bank as bank_router\n" if module == "diagnostic" else ""
    return ast.parse('if user.app_role == "student":\n' + local_import
                     + f"    bank_router._course_for_user({course}, user)\n").body[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=BASE)
    args = parser.parse_args()
    count = 0
    for module, names in ROUTES.items():
        path = f"services/api/app/routers/{module}.py"
        original = subprocess.check_output(["git", "show", f"{args.base}:{path}"], cwd=ROOT, text=True)
        before, after = ast.parse(original), ast.parse((ROOT / path).read_text())
        normalized = copy.deepcopy(after)
        if module != "diagnostic":
            imports = [i for i, n in enumerate(normalized.body) if dump(n) == dump(IMPORT)]
            assert len(imports) == 1, (module, "exactly one necessary import")
            del normalized.body[imports[0]]
        found = set()
        for node in normalized.body:
            if isinstance(node, ast.FunctionDef) and node.name in names:
                found.add(node.name)
                expected = guard(module, node.name)
                positions = [i for i, n in enumerate(node.body) if dump(n) == dump(expected)]
                assert len(positions) == 1, (module, node.name, "exact student branch")
                index = positions[0]
                expected_index = int(isinstance(node.body[0], ast.Expr)
                                     and isinstance(node.body[0].value, ast.Constant)
                                     and isinstance(node.body[0].value.value, str))
                if node.name == "get_conversation":
                    expected_index = 1
                    assert dump(node.body[0]) == dump(ast.parse(
                        "convo = _owned_conversation(conversation_id, user)").body[0])
                assert index == expected_index, (module, node.name, "admission placement")
                del node.body[index]
                count += 1
        assert found == names
        assert dump(before) == dump(normalized), (module, "non-admission change")
        print(module + ": exact student branches only; staff/mutations/helpers/responses unchanged")
    bank = "services/api/app/routers/bank.py"
    assert (ROOT / bank).read_bytes() == subprocess.check_output(["git", "show", f"{args.base}:{bank}"], cwd=ROOT)
    dashboard = "services/api/app/routers/dashboard.py"
    assert (ROOT / dashboard).read_bytes() == subprocess.check_output(["git", "show", f"{args.base}:{dashboard}"], cwd=ROOT)
    assert count == 19
    print("PASS: 19 exact guards; Bank helper and H dashboard byte-identical; H own-history AST unchanged")


if __name__ == "__main__":
    main()
