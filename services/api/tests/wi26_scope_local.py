"""Reproduce diagnostic admission-only scope proof against a pre-SEC revision.

Usage (Python 3.10+; API runtime 3.12+): cd services/api && uv run python tests/wi26_scope_local.py --base da765cbd27bd06c53c04ef3698c9410b503eb94a
Only AST-identical known admission statements are normalized. All remaining
module nodes, route signatures/decorators/bodies and non-route helpers compare.
"""
import argparse
import ast
import copy
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PATH = "services/api/app/routers/diagnostic.py"
ROUTES = {
    "get_roster", "get_content", "get_assessments", "propose_course_skills",
    "ingest_course", "ingest_status", "upload_course_content", "reset_tagging",
    "list_modules", "post_grade", "get_diagnostic_status", "get_diagnostic",
    "submit_diagnostic",
}
STAFF_DEPENDENCIES = {"get_roster", "ingest_course", "ingest_status"}


def dump(node):
    return ast.dump(node, include_attributes=False)


def expression(source):
    return ast.parse(source).body[0]


TEACH = expression("_assert_teaches_course(user=user, course_id=course_id)")
COURSE = expression("_course_ref(course_id, user.institution_id)")
STAFF_BLOCK = expression('''if user.app_role in {"instructor", "admin"}:
    _assert_teaches_course(user=user, course_id=course_id)
    _course_ref(course_id, user.institution_id)
''')
TRANSLATION = expression('''try:
    _assert_teaches_course(user=user, course_id=course_id)
except HTTPException as exc:
    if exc.status_code != status.HTTP_404_NOT_FOUND:
        raise
    raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient course access") from exc
''')
STUDENT_DEP = ast.parse("Depends(get_current_user)", mode="eval").body
STAFF_DEP = ast.parse("Depends(require_role('instructor', 'admin'))", mode="eval").body


def normalize_route(node, current):
    node = copy.deepcopy(node)
    if node.name in STAFF_DEPENDENCIES:
        pairs = zip(node.args.args[-len(node.args.defaults):], node.args.defaults, strict=True)
        indexes = [i for i, (arg, _) in enumerate(pairs) if arg.arg == "user"]
        assert len(indexes) == 1
        index = indexes[0]
        assert dump(node.args.defaults[index]) == dump(STAFF_DEP if current else STUDENT_DEP)
        node.args.defaults[index] = copy.deepcopy(STUDENT_DEP)
    body = []
    for statement in node.body:
        if dump(statement) in {dump(TEACH), dump(COURSE), dump(STAFF_BLOCK)}:
            continue
        if node.name in {"get_assessments", "post_grade"} and dump(statement) == dump(TRANSLATION):
            continue
        body.append(statement)
    node.body = body
    return node


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="00618c5d5b1bc16dc4f2f782d0f85ead6ef65bff")
    args = parser.parse_args()
    before = ast.parse(subprocess.check_output(["git", "show", f"{args.base}:{PATH}"], cwd=ROOT, text=True))
    after = ast.parse((ROOT / PATH).read_text())
    found = set()
    for tree, current in [(before, False), (after, True)]:
        for index, node in enumerate(tree.body):
            if isinstance(node, ast.FunctionDef) and any(
                isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                and isinstance(d.func.value, ast.Name) and d.func.value.id == "router"
                for d in node.decorator_list
            ):
                assert node.name in ROUTES, f"uninventoried route: {node.name}"
                found.add(node.name)
                tree.body[index] = normalize_route(node, current)
    assert found == ROUTES
    assert dump(before) == dump(after), "non-admission diagnostic AST change"
    print("PASS: all 13 routes, exact guard/dependency/translation allowances only")
    print("PASS: every non-route helper and remaining module AST unchanged")
    print("Routes:", ", ".join(sorted(found)))


if __name__ == "__main__":
    main()
