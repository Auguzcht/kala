#!/usr/bin/env python3
"""WI-24 bounded maintainer repair. No dependencies, dotenv or raw-row output.

Database errors are discarded, never logged. Input and backup are private local
files. Backup/restore staging is loopback-only. Hosted source execution requires
coordinator release and Fred gates; agents exercise only synthetic Docker sources.
"""
from __future__ import annotations

import argparse
import ast
import configparser
import math
import hashlib
import json
import os
from pathlib import Path
import re
import select
import stat
import subprocess
import shutil
import tempfile
import time
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "scripts/tests/identity_repair"
TABLES = (
    "enrollments", "evidence_events", "item_exposures", "item_reviews",
    "lms_identity_aliases", "mastery_state", "practice_answer_results",
    "quiz_set_attempts", "readiness_snapshots", "recommendations", "srs_state",
    "tutor_conversations", "user_profiles", "users",
)
GUARD_TABLES = ("audit_log", "consents", "data_subject_requests", "lti_launches", "tutor_attachments", "tutor_messages")
LOCK_TABLES = tuple(sorted(set(TABLES) | {
    "audit_log", "consents", "courses", "data_subject_requests", "generated_items",
    "lti_launches", "skills", "tutor_attachments", "tutor_messages", "quiz_sets",
}))
IMMUTABLE = {"evidence_events": "t_immutable", "item_reviews": "t_immutable",
             "practice_answer_results": "practice_answer_results_immutable"}
# Local design review is not a hosted execution release.
AUTH_EXCEPTION_REVISION = "bf750f7184c1e0ec718aba686d607f26ed08caff"


class Refused(Exception):
    """Fixed public reason code, never database exception text."""


def ident(value: str) -> str:
    if not re.fullmatch(r"[a-z_][a-z_0-9]*", value):
        raise Refused("UNEXPECTED_SCHEMA")
    return '"' + value + '"'


def literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


class Psql:
    """Persistent psql session: a transaction survives local backup operations."""
    def __init__(self, service: str, *, env=None, local_only=False):
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", service):
            raise Refused("INVALID_SERVICE_NAME")
        self.service = service
        inherited = os.environ.copy() if env is None else env.copy()
        # Service/passfile locations are the only inherited libpq settings.
        # In particular PGHOSTADDR/PGSERVICE/PGOPTIONS cannot redirect staging.
        self.env = {k: v for k, v in inherited.items()
                    if not k.startswith("PG") or k in {"PGSERVICEFILE", "PGPASSFILE"}}
        self.env["PYTHON_DOTENV_DISABLED"] = "1"
        if local_only:
            require_local_service(self)
        self.process = subprocess.Popen(
            ["psql", "-X", "-qAt", "-v", "ON_ERROR_STOP=1", "--no-password",
             "--dbname", "service=" + service], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=self.env,
            bufsize=0, umask=0o077,
        )
        self.buffer = b""
        self.run("SET timezone='UTC'; SET datestyle='ISO,YMD'; SET extra_float_digits=3;")

    def run(self, sql: str, *, timeout=45) -> list[str]:
        marker = "wi24_" + uuid.uuid4().hex
        try:
            self.process.stdin.write((sql + "\n\\echo " + marker + "\n").encode())
            self.process.stdin.flush()
        except (BrokenPipeError, OSError):
            raise Refused("DATABASE_OPERATION_FAILED") from None
        result = []
        deadline = time.monotonic() + timeout
        while True:
            while b"\n" in self.buffer:
                line, self.buffer = self.buffer.split(b"\n", 1)
                if line.decode() == marker:
                    return result
                if line:
                    result.append(line.decode())
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self.close()
                raise Refused("DATABASE_TIMEOUT")
            readable, _, _ = select.select([self.process.stdout], [], [], remaining)
            if not readable:
                continue
            data = os.read(self.process.stdout.fileno(), 65536)
            if not data:
                raise Refused("DATABASE_OPERATION_FAILED")
            self.buffer += data

    def scalar(self, sql):
        lines = self.run(sql)
        if len(lines) != 1:
            raise Refused("UNEXPECTED_DATABASE_RESPONSE")
        return json.loads(lines[0])

    def close(self):
        if self.process.poll() is None:
            self.process.kill()  # Server rolls back the open transaction on EOF.
        self.process.wait(timeout=5)
        for stream in (self.process.stdin, self.process.stdout):
            if stream:
                stream.close()


def private_file(path: Path, *, ignored=False):
    if any(p.is_symlink() for p in [path.absolute(), *path.absolute().parents]) or not path.is_file():
        raise Refused("PRIVATE_FILE_REQUIRED")
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise Refused("PRIVATE_FILE_MODE")
    if ignored:
        try:
            relative = path.resolve().relative_to(ROOT)
        except ValueError:
            raise Refused("GITIGNORED_INPUT_REQUIRED") from None
        result = subprocess.run(["git", "check-ignore", "-q", "--", str(relative)],
                                cwd=ROOT, capture_output=True)
        if result.returncode:
            raise Refused("GITIGNORED_INPUT_REQUIRED")


def read_pairs(path: Path):
    private_file(path, ignored=True)
    try:
        pairs = json.loads(path.read_text())
        if not isinstance(pairs, list) or not pairs or len(pairs) > 20:
            raise ValueError
        seen = set()
        for index, pair in enumerate(pairs, 1):
            if set(pair) != {"institution_id", "canonical_id", "legacy_id", "lms_uuid", "lti_sub", "course_ids"}:
                raise ValueError
            for name in ("institution_id", "canonical_id", "legacy_id"):
                pair[name] = str(uuid.UUID(pair[name]))
            if pair["canonical_id"] in seen or pair["legacy_id"] in seen or pair["canonical_id"] == pair["legacy_id"]:
                raise ValueError
            seen.update((pair["canonical_id"], pair["legacy_id"]))
            if not pair["lms_uuid"] or pair["lms_uuid"] != pair["lti_sub"] or pair["lms_uuid"].startswith("wi24-retired:"):
                raise ValueError
            if not isinstance(pair["course_ids"], list) or not pair["course_ids"]:
                raise ValueError
            pair["course_ids"] = sorted({str(uuid.UUID(c)) for c in pair["course_ids"]})
            pair["label"] = index
            pair["fingerprint"] = hashlib.sha256(json.dumps(pair, sort_keys=True).encode()).hexdigest()
        if len({p["institution_id"] for p in pairs}) != 1:
            raise ValueError
        return pairs
    except (ValueError, TypeError, KeyError, AttributeError):
        raise Refused("INVALID_PAIR_INPUT") from None


def create_pairs(db, pairs, directory):
    # COPY input avoids embedding real identifiers in SQL text/server query logs.
    db.run("CREATE TEMP TABLE wi24_input(document jsonb); CREATE TEMP TABLE wi24_pairs("
           "label integer, institution_id uuid, canonical_id uuid, legacy_id uuid,"
           "lms_uuid text, course_ids uuid[], fingerprint text, converged boolean default false); "
           "CREATE TEMP TABLE wi24_issues(label integer,reason text,n bigint); "
           "CREATE TEMP TABLE wi24_counts(label integer,table_name text,n bigint,collisions bigint default 0,legacy_losers bigint default 0);")
    payload = directory / "input.copy"
    # CSV quotes protect embedded tabs/newlines in opaque LMS identifiers.
    import csv
    with payload.open("x", newline="") as handle:
        os.chmod(payload, 0o600)
        csv.writer(handle).writerows([[json.dumps(p)] for p in pairs])
    db.run("\\copy wi24_input FROM " + literal(str(payload)) + " WITH (FORMAT csv)")
    db.run("INSERT INTO wi24_pairs(label,institution_id,canonical_id,legacy_id,lms_uuid,course_ids,fingerprint) "
           "SELECT (document->>'label')::integer,(document->>'institution_id')::uuid,"
           "(document->>'canonical_id')::uuid,(document->>'legacy_id')::uuid,document->>'lms_uuid',"
           "ARRAY(SELECT jsonb_array_elements_text(document->'course_ids'))::uuid[],document->>'fingerprint' "
           "FROM wi24_input;")
    payload.unlink()


def scope(table, alias="t"):
    if table == "tutor_messages":
        return (f"EXISTS(SELECT 1 FROM public.tutor_conversations c JOIN wi24_pairs p "
                f"ON c.user_id IN(p.canonical_id,p.legacy_id) WHERE c.id={alias}.conversation_id)")
    if table == "audit_log":
        refs = (f"{alias}.actor_id::text", f"{alias}.row_id", f"{alias}.old_data->>'user_id'",
                f"{alias}.new_data->>'user_id'", f"{alias}.old_data->>'id'", f"{alias}.new_data->>'id'")
        return "EXISTS(SELECT 1 FROM wi24_pairs p WHERE " + " OR ".join(
            f"({ref}) IN(p.canonical_id::text,p.legacy_id::text)" for ref in refs) + ")"
    column = "id" if table == "users" else "user_id"
    return f"EXISTS(SELECT 1 FROM wi24_pairs p WHERE {alias}.{column} IN (p.canonical_id,p.legacy_id))"


def begin(db, *, apply):
    db.run("BEGIN" + ("" if apply else " READ ONLY") + "; SET LOCAL lock_timeout='3s'; "
           "SET LOCAL statement_timeout='30s'; SET LOCAL idle_in_transaction_session_timeout='90s'; "
           "SET LOCAL request.jwt.claims='{}';")
    if apply:
        for table in LOCK_TABLES:
            db.run(f"LOCK TABLE public.{ident(table)} IN ACCESS EXCLUSIVE MODE;")


def schema(db):
    expected = (FIXTURE / "catalog.txt").read_text().splitlines()
    actual = db.run((FIXTURE / "catalog.sql").read_text())
    if sorted(actual) != sorted(expected):
        raise Refused("SCHEMA_DRIFT")
    return db.scalar("SELECT coalesce(jsonb_object_agg(table_name,columns),'{}') FROM ("
                     "SELECT table_name,jsonb_agg(jsonb_build_object('name',column_name,'type',"
                     "format_type(a.atttypid,a.atttypmod)) ORDER BY ordinal_position) columns "
                     "FROM information_schema.columns c JOIN pg_class r ON r.relname=c.table_name "
                     "JOIN pg_namespace n ON n.oid=r.relnamespace AND n.nspname=c.table_schema "
                     "JOIN pg_attribute a ON a.attrelid=r.oid AND a.attname=c.column_name "
                     "WHERE c.table_schema='public' GROUP BY table_name) x;")


def plan(db):
    db.run("DELETE FROM wi24_issues; DELETE FROM wi24_counts; "
           "UPDATE wi24_pairs p SET converged=(EXISTS(SELECT 1 FROM public.users u WHERE u.id=p.legacy_id "
           "AND u.lms_user_id='wi24-retired:'||p.legacy_id::text) AND EXISTS(SELECT 1 FROM public.audit_log a "
           "WHERE a.action='WI24_MERGE' AND a.metadata->'fingerprints' ? p.fingerprint));")
    def issue(reason, query):
        db.run("INSERT INTO wi24_issues SELECT label," + literal(reason) + ",n FROM (" + query + ") q WHERE n>0;")
    issue("IDENTITY_PROOF", "SELECT p.label,count(*) n FROM wi24_pairs p LEFT JOIN public.users c ON c.id=p.canonical_id "
          "LEFT JOIN public.users l ON l.id=p.legacy_id WHERE c.id IS NULL OR l.id IS NULL OR "
          "c.institution_id<>p.institution_id OR l.institution_id<>p.institution_id OR c.role<>l.role OR c.role<>'student' "
          "OR c.lms_user_id<>p.lms_uuid GROUP BY p.label")
    issue("COURSE_INPUT", "SELECT p.label,count(*) n FROM wi24_pairs p CROSS JOIN LATERAL unnest(p.course_ids) q(id) "
          "LEFT JOIN public.courses c ON c.id=q.id WHERE c.id IS NULL OR c.institution_id<>p.institution_id GROUP BY p.label")
    issue("CANONICAL_ALIAS_CONFLICT", "SELECT p.label,count(*) n FROM wi24_pairs p JOIN public.lms_identity_aliases a "
          "ON a.institution_id=p.institution_id AND a.lms_user_id=p.lms_uuid WHERE a.user_id<>p.canonical_id GROUP BY p.label")
    issue("MARKER_CONFLICT", "SELECT p.label,count(*) n FROM wi24_pairs p JOIN public.users l ON l.id=p.legacy_id "
          "WHERE (l.lms_user_id LIKE 'wi24-retired:%' AND NOT p.converged) OR EXISTS(SELECT 1 FROM public.users x "
          "WHERE x.institution_id=p.institution_id AND x.lms_user_id='wi24-retired:'||p.legacy_id::text AND x.id<>p.legacy_id) "
          "OR EXISTS(SELECT 1 FROM public.lms_identity_aliases a WHERE a.institution_id=p.institution_id "
          "AND a.lms_user_id='wi24-retired:'||p.legacy_id::text) GROUP BY p.label")
    issue("LEGACY_IDENTIFIER_ALIAS_CONFLICT", "SELECT p.label,count(*) n FROM wi24_pairs p JOIN public.users l ON l.id=p.legacy_id "
          "JOIN public.lms_identity_aliases a ON a.institution_id=p.institution_id AND a.lms_user_id=l.lms_user_id "
          "WHERE a.user_id NOT IN(p.canonical_id,p.legacy_id) GROUP BY p.label")
    issue("LEGACY_ALIAS_CONFLICT", "SELECT p.label,count(*) n FROM wi24_pairs p JOIN public.lms_identity_aliases a "
          "ON a.user_id=p.legacy_id JOIN public.users x ON x.institution_id=a.institution_id AND x.lms_user_id=a.lms_user_id "
          "WHERE x.id<>p.legacy_id GROUP BY p.label")
    issue("PROFILE_CONFLICT", "SELECT p.label,count(*) n FROM wi24_pairs p JOIN public.user_profiles c ON c.user_id=p.canonical_id "
          "JOIN public.user_profiles l ON l.user_id=p.legacy_id WHERE (to_jsonb(c)-'user_id'-'updated_at') "
          "IS DISTINCT FROM (to_jsonb(l)-'user_id'-'updated_at') GROUP BY p.label")
    for table, reason in (("consents", "CONSENT_PRESENT"), ("data_subject_requests", "DSR_PRESENT"),
                          ("tutor_attachments", "LEGACY_ATTACHMENTS")):
        owner = "t.user_id=p.legacy_id" if table == "tutor_attachments" else "t.user_id IN(p.canonical_id,p.legacy_id) AND NOT p.converged"
        issue(reason, f"SELECT p.label,count(*) n FROM wi24_pairs p JOIN public.{ident(table)} t ON {owner} GROUP BY p.label")
    for table in TABLES:
        if table == "users":
            continue
        db.run(f"INSERT INTO wi24_counts(label,table_name,n) SELECT p.label,{literal(table)},count(t.*) "
               f"FROM wi24_pairs p LEFT JOIN public.{ident(table)} t ON t.user_id=p.legacy_id GROUP BY p.label;")
        if table != "user_profiles":
            issue("TENANT_SCOPE", f"SELECT p.label,count(*) n FROM wi24_pairs p JOIN public.{ident(table)} t "
                  "ON t.user_id IN(p.canonical_id,p.legacy_id) WHERE t.institution_id<>p.institution_id GROUP BY p.label")
        if table not in {"lms_identity_aliases", "user_profiles"}:
            issue("COURSE_SCOPE", f"SELECT p.label,count(*) n FROM wi24_pairs p JOIN public.{ident(table)} t "
                  "ON t.user_id IN(p.canonical_id,p.legacy_id) LEFT JOIN public.courses c ON c.id=t.course_id "
                  "WHERE c.id IS NULL OR c.institution_id<>p.institution_id OR NOT(t.course_id=ANY(p.course_ids)) GROUP BY p.label")
    for table in ("item_reviews", "practice_answer_results"):
        issue("SOURCE_KEY_COLLISION", f"SELECT p.label,count(*) n FROM wi24_pairs p JOIN public.{ident(table)} c "
              "ON c.user_id=p.canonical_id JOIN public." + ident(table) + " l ON l.user_id=p.legacy_id "
              "AND c.idempotency_key=l.idempotency_key GROUP BY p.label")
    issue("SOURCE_SESSION_COLLISION", "SELECT p.label,count(*) n FROM wi24_pairs p JOIN public.item_reviews c "
          "ON c.user_id=p.canonical_id JOIN public.item_reviews l ON l.user_id=p.legacy_id "
          "AND c.item_id=l.item_id AND c.session_id=l.session_id WHERE c.counted AND l.counted AND c.session_id IS NOT NULL GROUP BY p.label")
    issue("ROLE_COLLISION", "SELECT p.label,count(*) n FROM wi24_pairs p JOIN public.enrollments c ON c.user_id=p.canonical_id "
          "JOIN public.enrollments l ON l.user_id=p.legacy_id AND l.course_id=c.course_id WHERE l.role<>c.role GROUP BY p.label")
    issue("UNFINISHED_ATTEMPTS", "SELECT label,count(*) n FROM (SELECT p.label,a.set_id FROM wi24_pairs p "
          "JOIN public.quiz_set_attempts a ON a.user_id IN(p.canonical_id,p.legacy_id) "
          "WHERE a.completed_at IS NULL GROUP BY p.label,a.set_id HAVING count(*)>1) x GROUP BY label")
    issue("INVALID_ATTEMPT_NUMBER", "SELECT p.label,count(*) n FROM wi24_pairs p JOIN public.quiz_set_attempts a "
          "ON a.user_id IN(p.canonical_id,p.legacy_id) WHERE a.attempt_number<=0 GROUP BY p.label")
    issue("AMBIGUOUS_ATTEMPT_LIFECYCLE", "SELECT p.label,count(*) n FROM wi24_pairs p JOIN public.quiz_set_attempts a "
          "ON a.user_id IN(p.canonical_id,p.legacy_id) WHERE a.completed_at IS NULL AND "
          "((a.user_id=p.canonical_id AND EXISTS(SELECT 1 FROM public.quiz_set_attempts l WHERE l.user_id=p.legacy_id AND l.set_id=a.set_id)) "
          "OR (a.user_id=p.legacy_id AND EXISTS(SELECT 1 FROM public.quiz_set_attempts l WHERE l.user_id=p.legacy_id "
          "AND l.set_id=a.set_id AND l.attempt_number>a.attempt_number))) GROUP BY p.label")
    issue("ATTEMPT_OVERFLOW", "SELECT label,count(*) n FROM (SELECT p.label,a.set_id,coalesce(max(a.attempt_number) FILTER(WHERE a.user_id=p.canonical_id),0)::integer + "
          "count(*) FILTER(WHERE a.user_id=p.legacy_id) upper_bound FROM wi24_pairs p "
          "JOIN public.quiz_set_attempts a ON a.user_id IN(p.canonical_id,p.legacy_id) "
          "GROUP BY p.label,a.set_id) q WHERE upper_bound>32767 GROUP BY label")
    issue("AMBIGUOUS_WORKER_ORDER", "SELECT label,count(*) n FROM(SELECT p.label,e.skill_id,e.created_at "
          "FROM wi24_pairs p JOIN public.evidence_events e ON e.user_id IN(p.canonical_id,p.legacy_id) "
          "WHERE e.skill_id IS NOT NULL GROUP BY p.label,e.skill_id,e.created_at "
          "HAVING count(DISTINCT coalesce(e.correct,false))>1) q GROUP BY label")
    issue("STALE_CANONICAL_MASTERY", "SELECT p.label,count(*) n FROM wi24_pairs p JOIN public.mastery_state m "
          "ON m.user_id=p.canonical_id WHERE NOT EXISTS(SELECT 1 FROM public.evidence_events e "
          "WHERE e.user_id IN(p.canonical_id,p.legacy_id) AND e.skill_id=m.skill_id AND e.course_id=m.course_id) GROUP BY p.label")
    issue("WORKER_CODE_CAP", "SELECT p.label,count(*) n FROM wi24_pairs p JOIN public.evidence_events e "
          "ON e.institution_id=p.institution_id WHERE NOT p.converged GROUP BY p.label HAVING count(*)>=50000")
    # Source tables without owner/tenant FKs need explicit relation checks.
    for table in ("item_reviews", "practice_answer_results", "srs_state", "item_exposures"):
        issue("ITEM_RELATION", f"SELECT p.label,count(*) n FROM wi24_pairs p JOIN public.{ident(table)} t "
              "ON t.user_id IN(p.canonical_id,p.legacy_id) LEFT JOIN public.generated_items i ON i.id=t.item_id "
              "WHERE i.id IS NULL OR i.institution_id<>p.institution_id OR i.course_id<>t.course_id GROUP BY p.label")
    for table in ("evidence_events", "mastery_state", "item_reviews", "practice_answer_results", "srs_state", "item_exposures", "recommendations"):
        issue("SKILL_RELATION", f"SELECT p.label,count(*) n FROM wi24_pairs p JOIN public.{ident(table)} t "
              "ON t.user_id IN(p.canonical_id,p.legacy_id) LEFT JOIN public.skills s ON s.id=t.skill_id "
              "WHERE t.skill_id IS NOT NULL AND (s.id IS NULL OR s.institution_id<>p.institution_id OR s.course_id<>t.course_id) GROUP BY p.label")
    issue("ATTEMPT_RELATION", "SELECT p.label,count(*) n FROM wi24_pairs p JOIN public.practice_answer_results r "
          "ON r.user_id IN(p.canonical_id,p.legacy_id) JOIN public.quiz_set_attempts a ON a.id=r.attempt_id "
          "WHERE a.user_id<>r.user_id OR a.course_id<>r.course_id OR a.institution_id<>p.institution_id OR a.set_id<>r.set_id GROUP BY p.label")
    issue("EXTERNAL_ATTEMPT_REFERENCE", "SELECT p.label,count(*) n FROM wi24_pairs p JOIN public.quiz_set_attempts a "
          "ON a.user_id IN(p.canonical_id,p.legacy_id) JOIN public.practice_answer_results r ON r.attempt_id=a.id "
          "WHERE r.user_id<>a.user_id OR r.institution_id<>p.institution_id OR r.course_id<>a.course_id GROUP BY p.label")
    issue("ATTACHMENT_RELATION", "SELECT p.label,count(*) n FROM wi24_pairs p JOIN public.tutor_attachments a "
          "ON a.user_id=p.canonical_id JOIN public.tutor_conversations c ON c.id=a.conversation_id "
          "WHERE a.institution_id<>p.institution_id OR c.institution_id<>p.institution_id "
          "OR c.user_id NOT IN(p.canonical_id,p.legacy_id) OR NOT(c.course_id=ANY(p.course_ids)) GROUP BY p.label")
    issue("EXTERNAL_ATTACHMENT_REFERENCE", "SELECT p.label,count(*) n FROM wi24_pairs p JOIN public.tutor_conversations c "
          "ON c.user_id IN(p.canonical_id,p.legacy_id) JOIN public.tutor_attachments a ON a.conversation_id=c.id "
          "WHERE a.user_id NOT IN(p.canonical_id,p.legacy_id) OR a.institution_id<>p.institution_id GROUP BY p.label")
    issue("EXPOSURE_OVERFLOW", "SELECT p.label,count(*) n FROM wi24_pairs p JOIN public.item_exposures c ON c.user_id=p.canonical_id "
          "JOIN public.item_exposures l ON l.user_id=p.legacy_id AND l.item_id=c.item_id WHERE c.times_tested::bigint+l.times_tested>2147483647 GROUP BY p.label")
    issue("EXPOSURE_AMBIGUOUS", "SELECT p.label,count(*) n FROM wi24_pairs p JOIN public.item_exposures c ON c.user_id=p.canonical_id "
          "JOIN public.item_exposures l ON l.user_id=p.legacy_id AND l.item_id=c.item_id "
          "WHERE EXISTS(SELECT 1 FROM public.item_exposures t WHERE t.item_id=c.item_id AND t.user_id IN(p.canonical_id,p.legacy_id) "
          "AND t.times_tested<>(SELECT count(*) FROM public.practice_answer_results r WHERE r.user_id=t.user_id AND r.item_id=t.item_id AND r.set_id IS NOT NULL)) GROUP BY p.label")
    issue("SET_RELATION", "SELECT p.label,count(*) n FROM wi24_pairs p JOIN public.quiz_set_attempts a "
          "ON a.user_id IN(p.canonical_id,p.legacy_id) JOIN public.quiz_sets s ON s.id=a.set_id "
          "WHERE s.institution_id<>p.institution_id OR s.course_id<>a.course_id GROUP BY p.label")
    for table in ("tutor_conversations",):
        issue("SKILL_RELATION", f"SELECT p.label,count(*) n FROM wi24_pairs p JOIN public.{ident(table)} t "
              "ON t.user_id IN(p.canonical_id,p.legacy_id) JOIN public.skills s ON s.id=t.skill_id "
              "WHERE s.institution_id<>p.institution_id OR s.course_id<>t.course_id GROUP BY p.label")
    for table in TABLES:
        if table in {"users", "user_profiles"}:
            continue
        issue("CONVERGENCE_CHANGED", f"SELECT p.label,count(*) n FROM wi24_pairs p JOIN public.{ident(table)} t "
              "ON t.user_id=p.legacy_id WHERE p.converged GROUP BY p.label")
    for table, key in (("srs_state","item_id"),("item_exposures","item_id"),("enrollments","course_id")):
        db.run(f"UPDATE wi24_counts x SET collisions=(SELECT count(*) FROM public.{ident(table)} l "
               f"JOIN public.{ident(table)} c ON c.{key}=l.{key} JOIN wi24_pairs p ON l.user_id=p.legacy_id "
               "AND c.user_id=p.canonical_id WHERE p.label=x.label) WHERE x.table_name=" + literal(table) + ";")
    db.run("UPDATE wi24_counts x SET legacy_losers=(SELECT count(*) FROM public.srs_state l JOIN public.srs_state c "
           "ON c.item_id=l.item_id JOIN wi24_pairs p ON l.user_id=p.legacy_id AND c.user_id=p.canonical_id "
           "WHERE p.label=x.label AND (coalesce(l.last_reviewed_at,'-infinity'),l.created_at) "
           "<=(coalesce(c.last_reviewed_at,'-infinity'),c.created_at)) WHERE table_name='srs_state';")
    db.run("UPDATE wi24_counts x SET collisions=(SELECT count(*) FROM public.quiz_set_attempts l JOIN public.quiz_set_attempts c "
           "ON c.set_id=l.set_id AND c.attempt_number=l.attempt_number JOIN wi24_pairs p ON l.user_id=p.legacy_id "
           "AND c.user_id=p.canonical_id WHERE p.label=x.label) WHERE table_name='quiz_set_attempts';")
    return db.scalar("SELECT jsonb_build_object('issues',coalesce((SELECT jsonb_agg(to_jsonb(i) ORDER BY label,reason) FROM wi24_issues i),'[]'),"
                     "'counts',coalesce((SELECT jsonb_agg(to_jsonb(c) ORDER BY label,table_name) FROM wi24_counts c),'[]'),"
                     "'pairs',(SELECT jsonb_agg(jsonb_build_object('label',label,'converged',converged) ORDER BY label) FROM wi24_pairs));")


def snapshot(db):
    result = {}
    for table in (*TABLES, *GUARD_TABLES):
        result[table] = db.scalar(f"SELECT jsonb_build_object('count',count(*),'hash',"
                                "encode(digest(coalesce(string_agg(to_jsonb(t)::text,E'\\n' ORDER BY to_jsonb(t)::text COLLATE \"C\"),''),'sha256'),'hex')) "
                                f"FROM public.{ident(table)} t WHERE {scope(table)};")
    return result


def require_local_service(local):
    # Validate the actual client endpoint, including Docker loopback forwards.
    # Never print the service file: it can also contain credentials.
    servicefile = Path(local.env.get("PGSERVICEFILE", str(Path.home() / ".pg_service.conf")))
    private_file(servicefile)
    config = configparser.ConfigParser(interpolation=None)
    config.read(servicefile)
    if local.service not in config:
        raise Refused("LOCAL_SERVICE_REQUIRED")
    values = config[local.service]
    allowed = {"host", "hostaddr", "port", "dbname", "user", "password", "passfile", "sslmode", "connect_timeout"}
    if set(values) - allowed or values.get("host") not in {"127.0.0.1", "::1"}:
        raise Refused("LOCAL_SERVICE_REQUIRED")
    if values.get("hostaddr", values["host"]) != values["host"]:
        raise Refused("LOCAL_SERVICE_REQUIRED")
    if not re.fullmatch(r"[a-zA-Z0-9_]+", values.get("dbname", "")):
        raise Refused("LOCAL_SERVICE_REQUIRED")
    if not values.get("port", "").isdigit() or not 1 <= int(values["port"]) <= 65535:
        raise Refused("LOCAL_SERVICE_REQUIRED")
    if values.get("sslmode", "disable") != "disable":
        raise Refused("LOCAL_SERVICE_REQUIRED")


def distinct_local(source, local):
    require_local_service(local)
    sql = ("SELECT jsonb_build_object('addr',inet_server_addr()::text,'database',current_database(),"
           "'major',current_setting('server_version_num')::integer/10000,'encoding',current_setting('server_encoding'));")
    source_info, local_info = source.scalar(sql), local.scalar(sql)
    if (source_info["addr"],source_info["database"]) == (local_info["addr"],local_info["database"]):
        raise Refused("SEPARATE_LOCAL_BACKUP_REQUIRED")
    if source_info["major"] != local_info["major"] or source_info["encoding"] != local_info["encoding"]:
        raise Refused("LOCAL_BINARY_COMPATIBILITY_REQUIRED")
    return source_info


def local_backup(source, local, directory, columns):
    source_info = distinct_local(source, local)
    if local.scalar("SELECT to_jsonb(to_regnamespace('wi24_backup') IS NOT NULL);"):
        raise Refused("BACKUP_DATABASE_NOT_EMPTY")
    before = snapshot(source)
    local.run("CREATE SCHEMA wi24_backup;")
    for table in TABLES:
        definition = ",".join(ident(c["name"]) + " " + c["type"] for c in columns[table])
        local.run(f"CREATE TABLE wi24_backup.{ident(table)}({definition});")
        path = directory / (table + ".bin")
        # Client-side binary files, never stdout or hosted schema objects.
        source.run(f"\\copy (SELECT t.* FROM public.{ident(table)} t WHERE {scope(table)}) TO {literal(str(path))} WITH (FORMAT binary)")
        os.chmod(path, 0o600)
        local.run(f"\\copy wi24_backup.{ident(table)} FROM {literal(str(path))} WITH (FORMAT binary)")
    audit_floor = source.scalar("SELECT to_jsonb(coalesce(max(id),0)) FROM public.audit_log;")
    manifest = {"preimage": before, "audit_floor": audit_floor, "columns": {t: columns[t] for t in TABLES}, "format": 1,
                "source_major": source_info["major"], "source_encoding": source_info["encoding"],
                "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "catalog_sha256": hashlib.sha256((FIXTURE / "catalog.txt").read_bytes()).hexdigest(),
                "migration_manifest_sha256": hashlib.sha256((FIXTURE / "migrations.sha256").read_bytes()).hexdigest()}
    private_json(directory / "manifest.json", manifest)
    archive = directory / "affected.dump"
    result = subprocess.run(["pg_dump", "--no-password", "--format=custom", "--no-owner", "--no-privileges",
                             "--schema=wi24_backup", "--dbname", "service=" + local.service,
                             "--file", str(archive)], env=local.env, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, timeout=60)
    if result.returncode:
        raise Refused("LOCAL_DUMP_FAILED")
    os.chmod(archive, 0o600)
    manifest["archive_sha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()
    private_json(directory / "manifest.json", manifest, replace=True)
    if snapshot(source) != before:
        raise Refused("PREIMAGE_CHANGED")
    return manifest


def private_json(path, value, *, replace=False):
    if path.is_symlink():
        raise Refused("PRIVATE_FILE_REQUIRED")
    flags = os.O_WRONLY | os.O_CREAT | (os.O_TRUNC if replace else os.O_EXCL)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "w") as handle:
        json.dump(value, handle, sort_keys=True)


def load_preimages(source, directory):
    for table in TABLES:
        source.run(f"CREATE TEMP TABLE pre_{table}(LIKE public.{ident(table)});")
        source.run(f"\\copy pre_{table} FROM {literal(str(directory / (table + '.bin')))} WITH (FORMAT binary)")


def reattribute(source, table):
    trigger = IMMUTABLE.get(table)
    if trigger:
        source.run(f"ALTER TABLE public.{ident(table)} DISABLE TRIGGER {ident(trigger)};")
    source.run(f"UPDATE public.{ident(table)} t SET user_id=p.canonical_id "
               f"FROM pre_{table} b JOIN wi24_pairs p ON b.user_id=p.legacy_id "
               "WHERE t.id=b.id AND t.user_id=b.user_id AND t.institution_id=p.institution_id;")
    if trigger:
        source.run(f"ALTER TABLE public.{ident(table)} ENABLE TRIGGER {ident(trigger)};")


def assert_true(db, predicate, reason):
    if not db.scalar("SELECT to_jsonb(" + predicate + ");"):
        raise Refused(reason)


def validate_triggers(db):
    for table, name in IMMUTABLE.items():
        assert_true(db, "EXISTS(SELECT 1 FROM pg_trigger WHERE tgrelid=" +
                    literal("public." + table) + "::regclass AND tgname=" + literal(name) +
                    " AND tgenabled='O')", "TRIGGER_STATE")
    assert_true(db, "NOT EXISTS(SELECT 1 FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid "
                "JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' "
                "AND NOT t.tgisinternal AND t.tgenabled<>'O')", "TRIGGER_STATE")


def apply_supported(db, *, inject_failure=False):
    """Only called after the locked plan, exact backup and all refusals pass."""
    assert_true(db, "NOT EXISTS(SELECT 1 FROM wi24_issues)", "BLOCKED_PAIR")
    validate_triggers(db)
    for table in IMMUTABLE:
        reattribute(db, table)
    if inject_failure:
        raise Refused("INJECTED_FAILURE")
    for table in ("recommendations", "tutor_conversations"):
        reattribute(db, table)
    # Same-role overlapping enrollment is redundant; the preimage is archived.
    db.run("DELETE FROM public.enrollments l USING wi24_pairs p,pre_enrollments c "
           "WHERE l.user_id=p.legacy_id AND c.user_id=p.canonical_id AND c.course_id=l.course_id; "
           "UPDATE public.enrollments e SET user_id=p.canonical_id FROM wi24_pairs p WHERE e.user_id=p.legacy_id;")
    # Compare whole review state. Canonical wins an exact timestamp tie.
    newer = "(coalesce(l.last_reviewed_at,'-infinity'),l.created_at) > (coalesce(c.last_reviewed_at,'-infinity'),c.created_at)"
    db.run("DELETE FROM public.srs_state t USING pre_srs_state l,pre_srs_state c,wi24_pairs p "
           "WHERE l.user_id=p.legacy_id AND c.user_id=p.canonical_id AND l.item_id=c.item_id "
           "AND t.item_id=l.item_id AND t.user_id=CASE WHEN " + newer +
           " THEN p.canonical_id ELSE p.legacy_id END; "
           "UPDATE public.srs_state t SET user_id=p.canonical_id FROM wi24_pairs p WHERE t.user_id=p.legacy_id;")
    # Move and renumber simultaneously: avoid transient uniqueness on legacy side.
    db.run("WITH numbered AS (SELECT l.id,p.canonical_id,(coalesce((SELECT max(c.attempt_number) "
           "FROM pre_quiz_set_attempts c WHERE c.user_id=p.canonical_id AND c.set_id=l.set_id),0) "
           "+row_number() OVER(PARTITION BY p.label,l.set_id ORDER BY l.attempt_number,l.id))::smallint n "
           "FROM pre_quiz_set_attempts l JOIN wi24_pairs p ON l.user_id=p.legacy_id) "
           "UPDATE public.quiz_set_attempts t SET user_id=x.canonical_id,attempt_number=x.n FROM numbered x WHERE t.id=x.id;")
    db.run("UPDATE public.item_exposures c SET last_studied_at=greatest(c.last_studied_at,l.last_studied_at), "
           "last_tested_at=greatest(c.last_tested_at,l.last_tested_at), "
           "last_correct=CASE WHEN coalesce(l.last_answered_at,'-infinity')>coalesce(c.last_answered_at,'-infinity') "
           "THEN l.last_correct ELSE c.last_correct END,last_answered_at=greatest(c.last_answered_at,l.last_answered_at), "
           "times_tested=c.times_tested+l.times_tested,created_at=least(c.created_at,l.created_at),updated_at=greatest(c.updated_at,l.updated_at) "
           "FROM pre_item_exposures l,wi24_pairs p WHERE l.user_id=p.legacy_id AND c.user_id=p.canonical_id AND c.item_id=l.item_id; "
           "DELETE FROM public.item_exposures l USING wi24_pairs p,pre_item_exposures c "
           "WHERE l.user_id=p.legacy_id AND c.user_id=p.canonical_id AND c.item_id=l.item_id; "
           "UPDATE public.item_exposures t SET user_id=p.canonical_id FROM wi24_pairs p WHERE t.user_id=p.legacy_id;")
    for table in ("mastery_state", "readiness_snapshots"):
        db.run(f"DELETE FROM public.{ident(table)} t USING wi24_pairs p WHERE t.user_id=p.legacy_id;")
    # AUTH-REQ-006 manual exception, committed before this implementation.
    db.run("UPDATE public.users u SET lms_user_id='wi24-retired:'||p.legacy_id::text FROM wi24_pairs p "
           "WHERE u.id=p.legacy_id AND NOT p.converged; "
           "UPDATE public.lms_identity_aliases a SET user_id=p.canonical_id FROM wi24_pairs p "
           "WHERE a.user_id=p.legacy_id AND a.institution_id=p.institution_id; "
           "INSERT INTO public.lms_identity_aliases(institution_id,lms_user_id,user_id,source) "
           "SELECT p.institution_id,b.lms_user_id,p.canonical_id,'backfill' FROM wi24_pairs p JOIN pre_users b ON b.id=p.legacy_id "
           "WHERE NOT p.converged ON CONFLICT(institution_id,lms_user_id) DO NOTHING;")
    # Historical actor references, launches, profiles and old audits stay untouched.
    for table in IMMUTABLE:
        assert_true(db, "NOT EXISTS(SELECT 1 FROM pre_" + table + " b LEFT JOIN public." + ident(table) +
                    " t ON t.id=b.id WHERE t.id IS NULL OR (to_jsonb(t)-'user_id') IS DISTINCT FROM "
                    "(to_jsonb(b)-'user_id'))", "SOURCE_PAYLOAD_CHANGED")
    assert_true(db, "NOT EXISTS(SELECT 1 FROM pre_evidence_events b LEFT JOIN public.evidence_events e ON e.id=b.id "
                "WHERE e.id IS NULL OR e.created_at IS DISTINCT FROM b.created_at)", "EVIDENCE_TIMESTAMP_CHANGED")
    for table in TABLES:
        if table in {"users", "user_profiles"}:
            continue
        assert_true(db, f"NOT EXISTS(SELECT 1 FROM public.{ident(table)} t JOIN wi24_pairs p ON t.user_id=p.legacy_id)",
                    "LEGACY_OWNERSHIP_REMAINS")
    assert_true(db, "NOT EXISTS(SELECT 1 FROM(SELECT b.*,p.canonical_id,row_number() OVER("
                "PARTITION BY p.label,b.item_id ORDER BY coalesce(b.last_reviewed_at,'-infinity') DESC,"
                "b.created_at DESC,(b.user_id=p.canonical_id) DESC) winner FROM pre_srs_state b "
                "JOIN wi24_pairs p ON b.user_id IN(p.canonical_id,p.legacy_id)) b "
                "LEFT JOIN public.srs_state t ON t.user_id=b.canonical_id AND t.item_id=b.item_id "
                "WHERE b.winner=1 AND (to_jsonb(t)-'user_id') IS DISTINCT FROM "
                "(to_jsonb(b)-'user_id'-'canonical_id'-'winner'))", "SCHEDULE_WINNER_MISMATCH")
    assert_true(db, "NOT EXISTS(SELECT 1 FROM pre_readiness_snapshots b JOIN wi24_pairs p ON b.user_id=p.canonical_id "
                "LEFT JOIN public.readiness_snapshots t ON t.id=b.id WHERE to_jsonb(t) IS DISTINCT FROM to_jsonb(b))",
                "CANONICAL_READINESS_CHANGED")
    assert_true(db, "NOT EXISTS(SELECT 1 FROM public.practice_answer_results r JOIN wi24_pairs p "
                "ON r.user_id IN(p.canonical_id,p.legacy_id) JOIN public.quiz_set_attempts a ON a.id=r.attempt_id "
                "WHERE a.user_id<>r.user_id OR a.set_id<>r.set_id)", "ANSWER_ATTEMPT_LINK")
    validate_triggers(db)
    db.run("INSERT INTO public.audit_log(institution_id,actor_role,action,table_name,metadata) "
           "SELECT p.institution_id,'maintainer','WI24_MERGE','users',jsonb_build_object("
           "'who',session_user,'when',transaction_timestamp(),'backup_sha256',(SELECT document->>'archive_sha256' FROM wi24_backup_meta),"
           "'worker_tracer_k',(SELECT document->'worker_tracer_k' FROM wi24_backup_meta),"
           "'worker_replay_sha256',(SELECT document->'worker_replay_sha256' FROM wi24_backup_meta),'fingerprints',jsonb_build_array(p.fingerprint),"
           "'canonical_id',p.canonical_id,'legacy_id',p.legacy_id,'original_lms_id',u.lms_user_id,"
           "'mapping_subject',p.lms_uuid,'counts',(SELECT jsonb_object_agg(table_name,n) FROM wi24_counts WHERE label=p.label)) "
           "FROM wi24_pairs p JOIN pre_users u ON u.id=p.legacy_id WHERE NOT p.converged;")


def table_hash(db, relation):
    return db.scalar("SELECT jsonb_build_object('count',count(*),'hash',"
                     "encode(sha256(convert_to(coalesce(string_agg(to_jsonb(t)::text,E'\\n' ORDER BY to_jsonb(t)::text COLLATE \"C\"),''),'UTF8')),'hex')) "
                     "FROM " + relation + " t;")


def verify_preimages(db, manifest):
    for table in TABLES:
        if table_hash(db, "pre_" + table) != manifest["preimage"][table]:
            raise Refused("BACKUP_PREIMAGE_MISMATCH")


def backup_metadata(source, directory, manifest):
    path = directory / "backup_meta.copy"
    import csv
    with path.open("x", newline="") as handle:
        os.chmod(path, 0o600)
        csv.writer(handle).writerow([json.dumps({key: manifest[key] for key in
            ("archive_sha256", "worker_tracer_k", "worker_replay_sha256")})])
    source.run("CREATE TEMP TABLE wi24_backup_meta(document jsonb);")
    source.run("\\copy wi24_backup_meta FROM " + literal(str(path)) + " WITH(FORMAT csv)")
    path.unlink()


def finish_backup(directory, manifest, source, pairs):
    manifest["postimage"] = snapshot(source)
    manifest["pairs"] = pairs
    manifest["auth_exception_revision"] = AUTH_EXCEPTION_REVISION
    private_json(directory / "manifest.json", manifest, replace=True)


def worker_replay():
    path = ROOT / "services/worker/app/jobs/reconcile_mastery.py"
    payload = path.read_bytes()
    tree = ast.parse(payload)
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_replay"]
    if len(nodes) != 1:
        raise Refused("WORKER_SOURCE_CHANGED")
    namespace = {}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),"exec"),namespace)
    return namespace["_replay"], hashlib.sha256(payload).hexdigest()


def capture_recompute(source, local, directory, *, worker_k):
    """Record exact post-worker derived rows while every other scoped row agrees.

    Does not run jobs, calculate/merge mastery or write derived state. Requires
    one completed worker readiness pass; later changes invalidate rollback.
    """
    source_info = distinct_local(source, local)
    private_file(directory / "manifest.json")
    private_file(directory / "affected.dump")
    manifest = json.loads((directory / "manifest.json").read_text())
    if source_info["major"] != manifest["source_major"] or source_info["encoding"] != manifest["source_encoding"]:
        raise Refused("LOCAL_BINARY_COMPATIBILITY_REQUIRED")
    if "recompute_sha256" in manifest:
        raise Refused("RECOMPUTE_ALREADY_CAPTURED")
    if worker_k != manifest.get("worker_tracer_k"):
        raise Refused("WORKER_K_CHANGED")
    replay, replay_hash = worker_replay()
    if replay_hash != manifest.get("worker_replay_sha256"):
        raise Refused("WORKER_SOURCE_CHANGED")
    if hashlib.sha256((directory / "affected.dump").read_bytes()).hexdigest() != manifest["archive_sha256"]:
        raise Refused("ARCHIVE_DIGEST_MISMATCH")
    create_pairs(source, manifest["pairs"], directory)
    begin(source, apply=True)
    columns = schema(source)
    validate_triggers(source)
    current = snapshot(source)
    derived = {"mastery_state", "readiness_snapshots"}
    if any(current[t] != manifest["postimage"][t] for t in current if t not in derived):
        raise Refused("NON_DERIVED_ACTIVITY_AFTER_APPLY")
    # Original typed files are verified against the archived preimage digests.
    # They are only used for comparison here, never to overwrite worker output.
    load_preimages(source, directory)
    verify_preimages(source, manifest)
    for table in derived:
        assert_true(source, f"NOT EXISTS(SELECT 1 FROM public.{ident(table)} t JOIN wi24_pairs p ON t.user_id=p.legacy_id)",
                    "LEGACY_DERIVED_REAPPEARED")
    assert_true(source, "NOT EXISTS(SELECT 1 FROM wi24_pairs p JOIN public.mastery_state m ON m.user_id=p.canonical_id "
                "WHERE NOT EXISTS(SELECT 1 FROM public.evidence_events e WHERE e.user_id=m.user_id AND e.skill_id=m.skill_id "
                "AND e.course_id=m.course_id) OR m.attempts<>(SELECT count(*) FROM public.evidence_events e "
                "WHERE e.user_id=m.user_id AND e.skill_id=m.skill_id AND e.course_id=m.course_id) OR "
                "m.last_seen IS DISTINCT FROM(SELECT max(e.created_at) FROM public.evidence_events e "
                "WHERE e.user_id=m.user_id AND e.skill_id=m.skill_id AND e.course_id=m.course_id))", "INCOMPLETE_MASTERY_REPLAY")
    assert_true(source, "NOT EXISTS(SELECT 1 FROM public.evidence_events e JOIN wi24_pairs p ON e.user_id=p.canonical_id "
                "WHERE e.skill_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.mastery_state m "
                "WHERE m.user_id=e.user_id AND m.skill_id=e.skill_id AND m.course_id=e.course_id))", "INCOMPLETE_MASTERY_REPLAY")
    assert_true(source, "NOT EXISTS(SELECT 1 FROM pre_readiness_snapshots b JOIN wi24_pairs p ON b.user_id=p.canonical_id "
                "LEFT JOIN public.readiness_snapshots t ON t.id=b.id WHERE to_jsonb(t) IS DISTINCT FROM to_jsonb(b))",
                "CANONICAL_READINESS_CHANGED")
    assert_true(source, "NOT EXISTS(SELECT e.user_id,e.skill_id,e.created_at FROM public.evidence_events e "
                "JOIN wi24_pairs p ON e.user_id=p.canonical_id WHERE e.skill_id IS NOT NULL "
                "GROUP BY e.user_id,e.skill_id,e.created_at HAVING count(DISTINCT coalesce(e.correct,false))>1)",
                "AMBIGUOUS_WORKER_ORDER")
    groups = source.scalar("SELECT coalesce(jsonb_agg(jsonb_build_object('estimate',m.estimate,'events',e.events)),'[]') FROM("
        "SELECT e.user_id,e.skill_id,jsonb_agg(jsonb_build_object('correct',e.correct) ORDER BY e.created_at) events "
        "FROM public.evidence_events e JOIN wi24_pairs p ON e.user_id=p.canonical_id WHERE e.skill_id IS NOT NULL "
        "GROUP BY e.user_id,e.skill_id) e JOIN public.mastery_state m ON m.user_id=e.user_id AND m.skill_id=e.skill_id;")
    if any(round(float(group["estimate"]),6) != round(replay(group["events"],k=worker_k),6) for group in groups):
        raise Refused("MASTERY_ESTIMATE_MISMATCH")
    source.run("CREATE TEMP VIEW wi24_new_readiness AS SELECT r.* FROM public.readiness_snapshots r "
               "JOIN wi24_pairs p ON r.user_id=p.canonical_id WHERE NOT EXISTS(SELECT 1 FROM pre_readiness_snapshots b WHERE b.id=r.id); "
               "CREATE TEMP VIEW wi24_expected_readiness AS SELECT e.user_id,e.course_id,round(avg(m.estimate),3) score "
               "FROM public.enrollments e JOIN wi24_pairs p ON e.user_id=p.canonical_id "
               "JOIN public.mastery_state m ON m.user_id=e.user_id AND m.course_id=e.course_id "
               "JOIN public.skills s ON s.id=m.skill_id AND s.status='approved' "
               "WHERE e.role='student' GROUP BY e.user_id,e.course_id;")
    assert_true(source, "NOT EXISTS(SELECT 1 FROM wi24_expected_readiness e LEFT JOIN wi24_new_readiness r "
                "ON r.user_id=e.user_id AND r.course_id=e.course_id GROUP BY e.user_id,e.course_id,e.score "
                "HAVING count(r.id)<>1 OR min(r.score)<>e.score) AND NOT EXISTS(SELECT 1 FROM wi24_new_readiness r "
                "WHERE NOT EXISTS(SELECT 1 FROM wi24_expected_readiness e WHERE e.user_id=r.user_id AND e.course_id=r.course_id))",
                "INCOMPLETE_READINESS_REPLAY")
    if local.scalar("SELECT to_jsonb(to_regnamespace('wi24_recompute') IS NOT NULL);"):
        raise Refused("RECOMPUTE_STAGING_NOT_EMPTY")
    local.run("CREATE SCHEMA wi24_recompute;")
    for table in sorted(derived):
        definition = ",".join(ident(c["name"]) + " " + c["type"] for c in columns[table])
        local.run(f"CREATE TABLE wi24_recompute.{ident(table)}({definition});")
        path = directory / ("recompute_" + table + ".bin")
        if path.exists():
            raise Refused("RECOMPUTE_FILES_ALREADY_EXIST")
        source.run(f"\\copy (SELECT t.* FROM public.{ident(table)} t WHERE {scope(table)}) TO {literal(str(path))} WITH(FORMAT binary)")
        os.chmod(path, 0o600)
        local.run(f"\\copy wi24_recompute.{ident(table)} FROM {literal(str(path))} WITH(FORMAT binary)")
        if table_hash(local, "wi24_recompute." + ident(table)) != current[table]:
            raise Refused("RECOMPUTE_COPY_MISMATCH")
    archive = directory / "recompute.dump"
    result = subprocess.run(["pg_dump", "--no-password", "--format=custom", "--no-owner", "--no-privileges",
                             "--schema=wi24_recompute", "--dbname", "service=" + local.service, "--file", str(archive)],
                            env=local.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
    if result.returncode:
        raise Refused("RECOMPUTE_DUMP_FAILED")
    archive.chmod(0o600)
    manifest["recompute_sha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()
    manifest["mastery_pairs_verified"] = len(groups)
    manifest["before_recompute"] = manifest["postimage"]
    manifest["postimage"] = current
    private_json(directory / "manifest.json", manifest, replace=True)
    meta = directory / "capture_meta.copy"
    import csv
    with meta.open("x", newline="") as handle:
        meta.chmod(0o600)
        csv.writer(handle).writerow([json.dumps({"archive_sha256": manifest["archive_sha256"],
                                               "recompute_sha256": manifest["recompute_sha256"],
                                               "derived_counts": {t: current[t]["count"] for t in derived},
                                               "worker_tracer_k": worker_k, "mastery_pairs_verified": len(groups),
                                               "worker_replay_sha256": replay_hash})])
    source.run("CREATE TEMP TABLE wi24_capture_meta(document jsonb);")
    source.run("\\copy wi24_capture_meta FROM " + literal(str(meta)) + " WITH(FORMAT csv)")
    meta.unlink()
    source.run("INSERT INTO public.audit_log(institution_id,actor_role,action,table_name,metadata) "
               "SELECT p.institution_id,'maintainer','WI24_RECOMPUTE_CAPTURE','users',"
               "m.document||jsonb_build_object('who',session_user,'when',transaction_timestamp(),'canonical_id',p.canonical_id,"
               "'legacy_id',p.legacy_id,'fingerprint',p.fingerprint) FROM wi24_pairs p CROSS JOIN wi24_capture_meta m;")
    source.run("COMMIT;")
    return {**{t: current[t]["count"] for t in sorted(derived)}, "mastery_pairs_verified": len(groups)}


def primary_keys(db):
    return db.scalar("SELECT jsonb_object_agg(relname,keys) FROM (SELECT c.relname,"
                     "jsonb_agg(a.attname ORDER BY key.ordinality) keys FROM pg_constraint k "
                     "JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace "
                     "CROSS JOIN LATERAL unnest(k.conkey) WITH ORDINALITY key(attnum,ordinality) "
                     "JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum=key.attnum "
                     "WHERE n.nspname='public' AND k.contype='p' GROUP BY c.relname) q;")


def restore_exact(source, local, directory, *, inject_failure=False):
    """Restore verified preimages only while the exact postimage still exists.

    Refuses ALL later activity/recompute in the pair scope. No deleting attempts,
    source rows or user anchors; old audit rows remain immutable. No hosted DDL.
    """
    source_info = distinct_local(source, local)
    private_file(directory / "manifest.json")
    private_file(directory / "affected.dump")
    manifest = json.loads((directory / "manifest.json").read_text())
    if source_info["major"] != manifest["source_major"] or source_info["encoding"] != manifest["source_encoding"]:
        raise Refused("LOCAL_BINARY_COMPATIBILITY_REQUIRED")
    if hashlib.sha256((directory / "affected.dump").read_bytes()).hexdigest() != manifest["archive_sha256"]:
        raise Refused("ARCHIVE_DIGEST_MISMATCH")
    if "postimage" not in manifest or "pairs" not in manifest:
        raise Refused("POSTIMAGE_MANIFEST_REQUIRED")
    if local.scalar("SELECT to_jsonb(to_regnamespace('wi24_backup') IS NOT NULL);"):
        raise Refused("RESTORE_DATABASE_NOT_EMPTY")
    result = subprocess.run(["pg_restore", "--no-password", "--no-owner", "--no-privileges", "--exit-on-error",
                             "--dbname", "service=" + local.service, str(directory / "affected.dump")],
                            env=local.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
    if result.returncode:
        raise Refused("LOCAL_ARCHIVE_RESTORE_FAILED")
    for table in TABLES:
        if table_hash(local, "wi24_backup." + ident(table)) != manifest["preimage"][table]:
            raise Refused("ARCHIVE_PREIMAGE_MISMATCH")
    create_pairs(source, manifest["pairs"], directory)
    begin(source, apply=True)
    actual_columns = schema(source)
    if manifest["columns"] != {table: actual_columns[table] for table in TABLES}:
        raise Refused("ARCHIVE_SCHEMA_MISMATCH")
    validate_triggers(source)
    if snapshot(source) != manifest["postimage"]:
        raise Refused("POSTIMAGE_CHANGED_RECOMPUTE_OR_ACTIVITY")
    work = Path(tempfile.mkdtemp(prefix="restore-", dir=directory))
    try:
        for table in TABLES:
            path = work / ("restore_" + table + ".bin")
            if path.exists():
                raise Refused("RESTORE_FILES_ALREADY_EXIST")
            local.run(f"\\copy wi24_backup.{ident(table)} TO {literal(str(path))} WITH (FORMAT binary)")
            os.chmod(path, 0o600)
            source.run(f"CREATE TEMP TABLE pre_{table}(LIKE public.{ident(table)});")
            source.run(f"\\copy pre_{table} FROM {literal(str(path))} WITH (FORMAT binary)")
        verify_preimages(source, manifest)
        if "recompute_sha256" in manifest:
            archive = directory / "recompute.dump"
            private_file(archive)
            if hashlib.sha256(archive.read_bytes()).hexdigest() != manifest["recompute_sha256"]:
                raise Refused("RECOMPUTE_ARCHIVE_DIGEST_MISMATCH")
            restored = subprocess.run(["pg_restore", "--no-password", "--no-owner", "--no-privileges", "--exit-on-error",
                                       "--dbname", "service=" + local.service, str(archive)], env=local.env,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
            if restored.returncode:
                raise Refused("RECOMPUTE_ARCHIVE_RESTORE_FAILED")
            for table in ("mastery_state", "readiness_snapshots"):
                if table_hash(local, "wi24_recompute." + ident(table)) != manifest["postimage"][table]:
                    raise Refused("RECOMPUTE_ARCHIVE_POSTIMAGE_MISMATCH")
        assert_true(source, "NOT EXISTS(SELECT 1 FROM wi24_pairs p WHERE NOT EXISTS(SELECT 1 FROM public.audit_log a "
                    "WHERE a.action='WI24_MERGE' AND a.metadata->'fingerprints' ? p.fingerprint AND "
                    "a.metadata->>'backup_sha256'=" + literal(manifest["archive_sha256"]) + "))", "MERGE_AUDIT_MISMATCH")
        if "recompute_sha256" in manifest:
            assert_true(source, "NOT EXISTS(SELECT 1 FROM wi24_pairs p WHERE NOT EXISTS(SELECT 1 FROM public.audit_log a "
                        "WHERE a.action='WI24_RECOMPUTE_CAPTURE' AND a.metadata->>'fingerprint'=p.fingerprint "
                        "AND a.metadata->>'recompute_sha256'=" + literal(manifest["recompute_sha256"]) + "))", "CAPTURE_AUDIT_MISMATCH")
        keys = primary_keys(source)
        # No deleting parent attempts, sources or identities: their PK sets never
        # change in this repair. A mismatch is corruption or scope expansion.
        no_delete = set(IMMUTABLE) | {"quiz_set_attempts", "users", "user_profiles", "recommendations", "tutor_conversations"}
        order = ("users", "quiz_set_attempts", "evidence_events", "item_reviews", "practice_answer_results",
                 "lms_identity_aliases", "enrollments", "srs_state", "item_exposures", "tutor_conversations",
                 "recommendations", "mastery_state", "readiness_snapshots", "user_profiles")
        for table in order:
            join = " AND ".join(f"t.{ident(k)}=b.{ident(k)}" for k in keys[table])
            missing_pre = f"NOT EXISTS(SELECT 1 FROM pre_{table} b WHERE {join})"
            if table in no_delete:
                assert_true(source, f"NOT EXISTS(SELECT 1 FROM public.{ident(table)} t WHERE {scope(table)} AND {missing_pre})",
                            "SOURCE_PK_SET_CHANGED")
            else:
                source.run(f"DELETE FROM public.{ident(table)} t WHERE {scope(table)} AND {missing_pre};")
            trigger = IMMUTABLE.get(table)
            # set_updated_at would destroy exact preimage timestamps on restoration.
            updated_trigger = "t_updated_at" if table in {"users", "mastery_state", "user_profiles"} else None
            triggers = [x for x in (trigger, updated_trigger) if x]
            for name in triggers:
                source.run(f"ALTER TABLE public.{ident(table)} DISABLE TRIGGER {ident(name)};")
            assignments = ",".join(f"{ident(c['name'])}=b.{ident(c['name'])}" for c in manifest["columns"][table])
            source.run(f"UPDATE public.{ident(table)} t SET {assignments} FROM pre_{table} b WHERE {join} "
                       "AND to_jsonb(t) IS DISTINCT FROM to_jsonb(b);")
            for name in reversed(triggers):
                source.run(f"ALTER TABLE public.{ident(table)} ENABLE TRIGGER {ident(name)};")
            colnames = ",".join(ident(c["name"]) for c in manifest["columns"][table])
            source.run(f"INSERT INTO public.{ident(table)}({colnames}) SELECT {colnames} FROM pre_{table} b "
                       f"WHERE NOT EXISTS(SELECT 1 FROM public.{ident(table)} t WHERE {join});")
            if inject_failure and table == "item_reviews":
                raise Refused("INJECTED_RESTORE_FAILURE")
        restored_image = snapshot(source)
        if any(restored_image[t] != manifest["preimage"][t] for t in restored_image if t != "audit_log"):
            raise Refused("RESTORE_PREIMAGE_MISMATCH")
        old_audit = source.scalar("SELECT jsonb_build_object('count',count(*),'hash',"
            "encode(digest(coalesce(string_agg(to_jsonb(t)::text,E'\\n' ORDER BY to_jsonb(t)::text COLLATE \"C\"),''),'sha256'),'hex')) "
            "FROM public.audit_log t WHERE " + scope("audit_log") + " AND t.id<=" + str(int(manifest["audit_floor"])) + ";")
        if old_audit != manifest["preimage"]["audit_log"]:
            raise Refused("ORIGINAL_AUDIT_PREFIX_CHANGED")
        validate_triggers(source)
        source.run("INSERT INTO public.audit_log(institution_id,actor_role,action,table_name,metadata) "
                   "SELECT p.institution_id,'maintainer','WI24_ROLLBACK','users',jsonb_build_object("
                   "'who',session_user,'when',transaction_timestamp(),'canonical_id',p.canonical_id,"
                   "'legacy_id',p.legacy_id,'fingerprints',jsonb_build_array(p.fingerprint)) FROM wi24_pairs p;")
        source.run("COMMIT;")
        return {"restored_pairs": len(manifest["pairs"]), "timestamp_mismatches": 0}
    finally:
        shutil.rmtree(work)


def emit_governance_refusal(report):
    counts = {}
    for row in report["issues"]:
        if row["reason"] not in {"CONSENT_PRESENT", "DSR_PRESENT"}:
            continue
        pair = counts.setdefault(row["label"], {"consent_count": 0, "dsr_count": 0})
        key = "consent_count" if row["reason"] == "CONSENT_PRESENT" else "dsr_count"
        pair[key] += row["n"]
    for label, pair in sorted(counts.items()):
        print(f"pair {label} refused: governance ambiguity consent_count={pair['consent_count']} dsr_count={pair['dsr_count']}")
    return bool(counts)


def emit(report):
    rules = {"srs_state":"latest_whole_state", "quiz_set_attempts":"append_attempt_numbers",
             "item_exposures":"verified_disjoint_counts", "enrollments":"same_role",
             "mastery_state":"delete_legacy_recompute", "readiness_snapshots":"delete_legacy_preserve_canonical",
             "user_profiles":"retain_identity_metadata", "lms_identity_aliases":"checked_redirect"}
    for row in report["counts"]:
        table, n, collisions = row["table_name"],row["n"],row["collisions"]
        moved, deleted, retained = n,0,0
        if table in {"mastery_state","readiness_snapshots"}: moved,deleted=0,n
        elif table == "user_profiles": moved,retained=0,n
        elif table in {"item_exposures","enrollments"}: moved,deleted=n-collisions,collisions
        elif table == "srs_state": moved,deleted=n-row["legacy_losers"],collisions
        print(f"pair {row['label']} {table} move={moved} delete={deleted} retained_metadata={retained} "
              f"collisions={collisions} rule={rules.get(table,'reattribute')}")
    for pair in report["pairs"]:
        print(f"pair {pair['label']} converged={str(pair['converged']).lower()}")
    for row in report["issues"]:
        print(f"pair {row['label']} blocked_count={row['n']} reason={row['reason']}")


def main():
    if sys.version_info < (3,10):
        print("blocked=true reason=PYTHON_310_REQUIRED")
        return 2
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-service", required=True)
    parser.add_argument("--backup-service")
    parser.add_argument("--private-directory", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--restore", action="store_true")
    parser.add_argument("--capture-recompute", action="store_true")
    parser.add_argument("--worker-tracer-k", type=float)
    parser.add_argument("--confirm-worker-config", action="store_true")
    parser.add_argument("--local-test-failure", choices=("after_sources", "during_restore"), help=argparse.SUPPRESS)
    args = parser.parse_args()
    source = local = None
    try:
        if args.apply != args.confirm or ((args.restore or args.capture_recompute) and not args.apply) or (args.restore and args.capture_recompute):
            raise Refused("BOTH_APPLY_CONFIRM_REQUIRED")
        if args.apply and not args.restore and (not args.confirm_worker_config or args.worker_tracer_k is None
                or not math.isfinite(args.worker_tracer_k) or not 0 < args.worker_tracer_k <= 1):
            raise Refused("CONFIRMED_WORKER_K_REQUIRED")
        if args.apply and not AUTH_EXCEPTION_REVISION:
            raise Refused("AUTH_EXCEPTION_REQUIRED")
        # Reject psql metacommand/path injection and symlinked destinations.
        raw_directory = args.private_directory.absolute()
        if not re.fullmatch(r"[a-zA-Z0-9_./-]+", str(raw_directory)):
            raise Refused("PRIVATE_DIRECTORY_REQUIRED")
        if any(parent.is_symlink() for parent in [raw_directory, *raw_directory.parents]):
            raise Refused("PRIVATE_DIRECTORY_REQUIRED")
        directory = raw_directory.resolve()
        try:
            relative_directory = directory.relative_to(ROOT)
        except ValueError:
            relative_directory = None
        if relative_directory is not None:
            ignored = subprocess.run(["git","check-ignore","-q","--",str(relative_directory)],cwd=ROOT,capture_output=True)
            if ignored.returncode:
                raise Refused("GITIGNORED_OUTPUT_REQUIRED")
        if args.restore or args.capture_recompute:
            if not directory.is_dir() or stat.S_IMODE(directory.stat().st_mode) != 0o700:
                raise Refused("PRIVATE_DIRECTORY_REQUIRED")
        else:
            directory.mkdir(mode=0o700, parents=False, exist_ok=False)
        pairs = read_pairs(args.input)
        source = Psql(args.source_service, local_only=bool(args.local_test_failure))
        if args.restore or args.capture_recompute:
            private_file(directory / "manifest.json")
            saved = json.loads((directory / "manifest.json").read_text())
            if saved.get("pairs") != pairs or not args.backup_service:
                raise Refused("RESTORE_INPUT_MISMATCH")
            local = Psql(args.backup_service, local_only=True)
            if args.capture_recompute:
                result = capture_recompute(source, local, directory, worker_k=args.worker_tracer_k)
                print("recompute_captured=true mastery_rows=" + str(result["mastery_state"]) +
                      " readiness_rows=" + str(result["readiness_snapshots"]) +
                      " mastery_pairs_verified=" + str(result["mastery_pairs_verified"]) + " estimate_mismatches=0 k_confirmed=true")
            else:
                result = restore_exact(source, local, directory, inject_failure=args.local_test_failure == "during_restore")
                print(f"restored_pairs={result['restored_pairs']} timestamp_mismatches=0")
            return 0
        create_pairs(source, pairs, directory)
        begin(source, apply=args.apply)
        columns = schema(source)
        validate_triggers(source)
        report = plan(source)
        if emit_governance_refusal(report):
            source.run("ROLLBACK;")
            return 2
        emit(report)
        if report["issues"]:
            raise Refused("BLOCKED_PAIR")
        if all(pair["converged"] for pair in report["pairs"]):
            source.run("ROLLBACK;")
            print("converged=true source_writes=0")
            return 0
        if not args.apply:
            source.run("ROLLBACK;")
            print("dry_run=true source_writes=0")
            return 0
        if not args.backup_service:
            raise Refused("LOCAL_BACKUP_SERVICE_REQUIRED")
        local = Psql(args.backup_service, local_only=True)
        manifest = local_backup(source, local, directory, columns)
        manifest["worker_tracer_k"] = args.worker_tracer_k
        manifest["worker_replay_sha256"] = worker_replay()[1]
        private_json(directory / "manifest.json", manifest, replace=True)
        load_preimages(source, directory)
        verify_preimages(source, manifest)
        backup_metadata(source, directory, manifest)
        if snapshot(source) != manifest["preimage"]:
            raise Refused("PREIMAGE_CHANGED")
        apply_supported(source, inject_failure=args.local_test_failure == "after_sources")
        finish_backup(directory, manifest, source, pairs)
        source.run("COMMIT;")
        print("applied_pairs=" + str(sum(not p["converged"] for p in report["pairs"])) +
              " timestamp_mismatches=0 legacy_learner_rows=0 triggers_restored=true")
        return 0
    except Refused as error:
        print("blocked=true reason=" + str(error))
        return 2
    except KeyboardInterrupt:
        print("blocked=true reason=INTERRUPTED")
        return 130
    except Exception:
        # Never render database/input objects or tracebacks containing payloads.
        print("blocked=true reason=INTERNAL_OR_IO_FAILURE")
        return 2
    finally:
        if source:
            source.close()
        if local:
            local.close()


if __name__ == "__main__":
    raise SystemExit(main())
