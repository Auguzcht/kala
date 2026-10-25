"""Compile unchanged application function bodies with synthetic local DB adapters.

No application configuration/import side effects, dotenv or network transports.
These adapters exercise exact resolver/job logic, not hosted HTTP acceptance.
"""
import ast
import json
from pathlib import Path
from types import SimpleNamespace


class LocalDB:
    def __init__(self, connection, quote, *, cap=None):
        self.connection = connection
        self.quote = quote
        self.cap = cap

    def select(self, table, params):
        columns = params.get("select", "*")
        projection = "*" if columns == "*" else ",".join('"' + c + '"' for c in columns.split(","))
        filters = []
        for name, value in params.items():
            if name in {"select", "order", "limit"}: continue
            if value.startswith("eq."):
                filters.append('"' + name + '"=' + self.quote(value[3:]))
            elif value.startswith("in.(") and value.endswith(")"):
                filters.append('"' + name + '" IN(' + ",".join(self.quote(v) for v in value[4:-1].split(",")) + ")")
            else:
                raise AssertionError("unexpected synthetic adapter filter")
        query = "SELECT " + projection + ' FROM public."' + table + '"'
        if filters: query += " WHERE " + " AND ".join(filters)
        if "order" in params:
            field, direction = params["order"].split(".")
            assert direction in {"asc", "desc"}
            query += ' ORDER BY "' + field + '" ' + direction
        limit = int(params.get("limit", 50000))
        if self.cap is not None: limit = min(limit, self.cap)
        query += " LIMIT " + str(limit)
        return self.connection.scalar("SELECT coalesce(jsonb_agg(to_jsonb(t)),'[]') FROM(" + query + ") t;")

    def write(self, table, rows, conflict=None):
        if isinstance(rows, dict): rows = [rows]
        for row in rows:
            columns = list(row)
            quoted = [f'"{c}"' for c in columns]
            record = "jsonb_populate_record(NULL::public." + table + "," + self.quote(json.dumps(row)) + "::jsonb)"
            statement = "INSERT INTO public." + table + "(" + ",".join(quoted) + ") SELECT "
            statement += ",".join(f"({record}).{c}" for c in quoted)
            if conflict:
                statement += " ON CONFLICT(" + conflict + ") DO UPDATE SET "
                statement += ",".join(f"{c}=excluded.{c}" for c in quoted)
            self.connection.run(statement + ";")

    def insert(self, table, rows): self.write(table, rows)
    def upsert(self, table, rows, on_conflict): self.write(table, rows, on_conflict)


def functions(path, names, namespace):
    tree = ast.parse(Path(path).read_text())
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in nodes} == set(names)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


def resolver(root, db):
    def by_id(user_id):
        rows = db.select("users", {"id": "eq." + user_id, "select": "*"})
        return rows[0] if rows else None
    def unexpected(**_): raise AssertionError("resolver unexpectedly created identity")
    namespace = {"select": db.select, "_user_by_id": by_id, "_touch_profile": lambda **_: None,
                 "record_identity_alias": lambda **_: None, "upsert": unexpected}
    return functions(root / "services/api/app/db/supabase.py", {"resolve_user"}, namespace)["resolve_user"]


def worker(root, db):
    namespace = {"db": db, "get_settings": lambda: SimpleNamespace(tracer_k=0.15)}
    mastery = functions(root / "services/worker/app/jobs/reconcile_mastery.py", {"_replay", "run"}, namespace.copy())["run"]
    readiness = functions(root / "services/worker/app/jobs/readiness_snapshot.py", {"run"}, namespace.copy())["run"]
    return mastery, readiness
