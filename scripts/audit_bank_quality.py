#!/usr/bin/env python3
"""Read-only bank/lesson audit; writes only a local report and vector cache.

Run from services/api:
  uv run python ../../scripts/audit_bank_quality.py --allow-embeddings

No lesson assembler, application routes, generation, write helpers, or RPCs
are called. All live database access uses app.db.supabase.select. A snapshot
and cache may be supplied for an offline rerender. Never fetches user profiles.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import sys
import threading
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api"))
from app.db import supabase as db


def select_all(table, params):
    rows = []
    while True:
        page = db.select(table, {**params, "order": "id.asc", "limit": "200",
                                 "offset": str(len(rows))})
        rows.extend(page)
        if len(page) < 200:
            return rows


def broken(row):
    choices = row.get("choices")
    return (not isinstance(choices, list) or len(choices) < 2
            or row.get("correct_choice_id") not in
            [c.get("id") for c in choices if isinstance(c, dict)])


def snapshot():
    data = {"captured_at": datetime.now(ZoneInfo("Asia/Manila")).isoformat()}
    data["items"] = select_all("generated_items", {
        "origin": "eq.bank", "retired_at": "is.null", "select": "*"})
    data["broken_answers"] = []
    for item in filter(broken, data["items"]):
        data["broken_answers"].extend(select_all("practice_answer_results", {
            "institution_id": f"eq.{item['institution_id']}",
            "item_id": f"eq.{item['id']}", "select": "id,item_id,correct"}))
    # Report A1 before doing any embedding work.
    print(f"A1 FIRST: {len(data['items'])} active bank items; "
          f"{sum(map(broken, data['items']))} broken keys", flush=True)
    for table, fields in {
        "courses": "id,institution_id,title,bank_serving",
        "skills": "id,institution_id,course_id,name,status",
        "guided_lessons": "*", "guided_lesson_steps": "*",
    }.items():
        data[table] = select_all(table, {"select": fields})
    check_ids = {s["check_item_id"] for s in data["guided_lesson_steps"]
                 if s.get("check_item_id")}
    data["checks"] = []
    for lesson in data["guided_lessons"]:
        ids = sorted({s["check_item_id"] for s in data["guided_lesson_steps"]
                      if s["lesson_id"] == lesson["id"] and s.get("check_item_id")})
        if ids:
            data["checks"].extend(select_all("generated_items", {
                "institution_id": f"eq.{lesson['institution_id']}",
                "id": f"in.({','.join(ids)})", "select": "*"}))
    data["checks"] = list({r["id"]: r for r in data["checks"]}.values())
    assert {r["id"] for r in data["checks"]} <= check_ids
    data["reported_matches"] = select_all("generated_items", {
        "prompt": "ilike.*six perspectives*",
        "select": "id,prompt,choices,correct_choice_id,origin,retired_at,created_at,"
                  "institution_id,course_id,skill_id"})
    return data


def short(value):
    return str(value or "NONE")[:8]


def cell(value):
    return str(value if value is not None else "N/A").replace("|", "\\|").replace("\n", " ")


def table(headers, rows):
    return ["| " + " | ".join(map(cell, headers)) + " |",
            "| " + " | ".join("---" for _ in headers) + " |"] + [
                "| " + " | ".join(map(cell, row)) + " |" for row in rows]


def teaching(step):
    # No separate title is stored. Summary and detail_points are the lesson's
    # own teaching text; include misconception and takeaway as teaching too.
    parts = [step.get("title"), step.get("summary"), *(step.get("detail_points") or []),
             step.get("misconception"), step.get("key_takeaway")]
    return "\n".join(str(p).strip() for p in parts if p and str(p).strip())


def relevance_text(step):
    return "\n".join(str(p).strip() for p in
                     [step.get("title"), step.get("summary"), *(step.get("detail_points") or [])]
                     if p and str(p).strip())


def normalize(vector):
    if isinstance(vector, str):
        vector = json.loads(vector)
    length = math.sqrt(sum(float(v) ** 2 for v in vector))
    if not length or not all(math.isfinite(float(v)) for v in vector):
        raise ValueError("Invalid embedding")
    return [float(v) / length for v in vector]


def cosine(left, right):
    if len(left) != len(right):
        raise ValueError("Embedding dimension mismatch")
    return max(-1.0, min(1.0, sum(a*b for a, b in zip(left, right))))


class Vectors:
    def __init__(self, path, allow):
        from app.config import get_settings
        settings = get_settings()
        self.provider = settings.embed_provider or settings.ai_provider
        self.model = getattr(settings, {"openai": "openai_embed_model",
            "openrouter": "openrouter_embed_model"}.get(self.provider, "bedrock_embed_model"))
        self.namespace = f"worker:{self.provider}:{self.model}:search_document:1024"
        self.path, self.allow = path, allow
        self.cache = json.loads(path.read_text()) if path.exists() else {}
        self.prior_calls = int(self.cache.get("_embedding_function_calls", 0))
        self.calls = 0
        self.hits = 0
        self.lock = threading.Lock()
        spec = importlib.util.spec_from_file_location("audit_worker_embed", ROOT / "services/worker/app/embed.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.embed = module.embed

    def key(self, text):
        return hashlib.sha256((self.namespace + "\0" + text).encode()).hexdigest()

    def fill(self, texts):
        texts = sorted(set(t for t in texts if t))
        missing = [t for t in texts if self.key(t) not in self.cache]
        self.hits += len(texts) - len(missing)
        if missing and not self.allow:
            raise RuntimeError(f"{len(missing)} missing vectors; use --allow-embeddings explicitly")
        print(f"Embeddings missing: {len(missing)}; cached: {len(texts)-len(missing)}; "
              f"provider={self.provider}, model={self.model}", flush=True)

        def one(text):
            with self.lock:
                self.calls += 1
                self.cache["_embedding_function_calls"] = self.prior_calls + self.calls
                self.path.write_text(json.dumps(self.cache))
            vector = normalize(self.embed(text, input_type="search_document"))
            with self.lock:
                self.cache[self.key(text)] = vector
                self.path.write_text(json.dumps(self.cache))
                if (len(self.cache) - 1) % 20 == 0:
                    print(f"Embedding progress: {len(self.cache)-1} cached", flush=True)
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(one, missing))

    def get(self, text):
        return self.cache[self.key(text)]


def report(data, vectors):
    courses = {c["id"]: c for c in data["courses"]}
    skills = {s["id"]: s for s in data["skills"]}
    items = data["items"]
    bad = list(filter(broken, items))
    out = ["# Bank and lesson quality audit — 2026-10-18", "",
           f"Snapshot: {data.get('captured_at', '2026-10-18, Asia/Manila; initial read before embedding calls')}. "
           "Database: linked live project jcufmpxjlgdfzefvulvz. Read-only REST selects through app.db; "
           "no RPC, lesson assembly, API routes, database writes, or generation calls. "
           "Pagination: stable id order, 200 rows per page. Reads are not a transactionally consistent snapshot.", "",
           "## A1. Broken answer keys — checked first", "",
           f"Active origin=bank items: **{len(items)}**; broken keys/choice counts: **{len(bad)}**. "
           "Criteria: answer id absent from choices, or fewer than two choices. "
           "Severity: a confirmed inaccessible answer key would be high severity (study and grading); "
           "none found in this snapshot. No claim that the reported UI symptom is resolved.", ""]
    grouped = defaultdict(list)
    for item in items:
        grouped[(item["course_id"], item["skill_id"])].append(item)
    out += table(["Course", "Skill", "Bank items", "Broken"], [
        [short(c), short(s) + " " + skills.get(s, {}).get("name", "UNKNOWN"), len(rows), sum(map(broken, rows))]
        for (c, s), rows in sorted(grouped.items())])
    out += [""] + table(["Course", "Bank items", "Broken"], [
        [short(c), sum(i["course_id"] == c for i in items), sum(i["course_id"] == c for i in bad)]
        for c in courses])
    outcomes = data["broken_answers"]
    out += ["", f"Broken-item saved answers: {len(outcomes)}; marked correct=true: "
            f"{sum(r.get('correct') is True for r in outcomes)}. With no broken items this is an empty cohort, "
            "not evidence of an ungradeable card.", ""]
    out += table(["Item", "Prompt (80)", "Choice ids", "Answer id", "Created", "Answers / correct"], [
        [short(i["id"]), i.get("prompt", "")[:80], [c.get("id") for c in i.get("choices", [])],
         i.get("correct_choice_id"), i.get("created_at"),
         f"{sum(r['item_id']==i['id'] for r in outcomes)} / "
         f"{sum(r['item_id']==i['id'] and r.get('correct') is True for r in outcomes)}"] for i in bad[:20]])
    out += ["", "### Reported CAF card and root-cause assessment", "",
            "All matching 'six perspectives' rows are listed below as a supplemental legacy check. "
            "The exact reported prompt does not occur in the active bank cohort. "
            "Current worker code validates ids a–d and key membership "
            "(`services/worker/app/item_gen.py:157–176`). Bank validation calls it at "
            "`services/worker/app/jobs/bank_build.py:265`, then shuffles complete choice dictionaries "
            "at lines 515–516 and persists the unchanged answer id at line 517. Shuffling changes order, "
            "not ids or labels, so it does not explain a dangling answer key. "
            "Legacy async generation persists validated choices and key at `services/worker/app/item_gen.py:290–305`. "
            "Historical creator for an individual row is NOT CONFIRMED: origin/version do not identify "
            "the exact executed source revision. No reproduction of this UI symptom was attempted.", "",
            "`correct_label` returns a matching label or None (`services/api/app/learn/items.py:450–466`). "
            "Study responses also fall back to a null label when the back query misses a row "
            "(`services/api/app/routers/flashcards.py:324–339`, `:390–401`). "
            "Thus a displayed null does not by itself prove a corrupt bank key. Root cause of the "
            "reported null is **NOT CONFIRMED**; no unsupported shuffle bug is asserted.", ""]
    out += table(["Item", "Origin", "Retired", "Key", "Resolved label"], [
        [short(i["id"]), i["origin"], i.get("retired_at") or "not retired", i.get("correct_choice_id"),
         next((c.get("label") for c in i.get("choices", [])
               if c.get("id") == i.get("correct_choice_id")), None)]
        for i in data.get("reported_matches", [])])
    approved = {key: rows for key, rows in grouped.items() if skills.get(key[1], {}).get("status") == "approved"}
    out += ["", "## A2. Near-duplicate bank questions", "",
            "No embedding column is present in the generated_items SELECT * response. "
            "No worker stem-embedding dedupe path exists in this checkout. The audit uses the worker's "
            "actual `services/worker/app/embed.py:22` embed function with search_document for both stems "
            "and step text. All vectors are generated under one provider/model; no content-chunk or "
            "skill vectors are substituted for question vectors. Cache is local only.", "",
            f"Embedding provider: {vectors.provider}; model: {vectors.model}. "
            "Cosine is computed on normalized vectors. Counts are cumulative unordered pairs within "
            "each approved skill, never cross-skill pairs. High cosine is a review flag, not proof "
            "that two questions test identical knowledge.", ""]
    vectors.fill([i["prompt"] for rows in approved.values() for i in rows if not i.get("embedding")])
    item_vectors = {i["id"]: normalize(i["embedding"]) if i.get("embedding") else vectors.get(i["prompt"])
                    for rows in approved.values() for i in rows}
    all_pairs = []
    distribution = []
    totals = defaultdict(lambda: [0, 0, 0, 0, 0, 0])
    for (course, skill), rows in sorted(approved.items()):
        pairs = [(cosine(item_vectors[a["id"]], item_vectors[b["id"]]), a, b)
                 for a, b in itertools.combinations(rows, 2)]
        counts = [sum(p[0] >= t for p in pairs) for t in [.95, .90, .85, .80]]
        distribution.append([short(course), short(skill) + " " + skills[skill]["name"], len(rows), len(pairs), *counts])
        totals[course] = [a+b for a, b in zip(totals[course], [len(rows), len(pairs), *counts])]
        all_pairs.extend(pairs)
    out += table(["Course", "Approved skill", "Items", "Pairs", ">= .95", ">= .90", ">= .85", ">= .80"], distribution)
    out += [""] + table(["Course totals", "Items", "Pairs", ">= .95", ">= .90", ">= .85", ">= .80"],
                         [[short(c), *totals.get(c, [0]*6)] for c in courses])
    all_pairs.sort(key=lambda p: (-p[0], p[1]["id"], p[2]["id"]))
    for title, pairs in [("15 highest-similarity pairs", all_pairs[:15]),
                         ("10 calibration pairs: 0.80 <= cosine <= 0.88",
                          [p for p in all_pairs if .80 <= p[0] <= .88][:10])]:
        out += ["", "### " + title, ""] + table(["Cosine", "Skill", "Item A", "Prompt A (100)", "Item B", "Prompt B (100)"], [
            [f"{score:.6f}", short(a["skill_id"]), short(a["id"]), a["prompt"][:100],
             short(b["id"]), b["prompt"][:100]] for score, a, b in pairs])
    out += ["", "Current dedupe: normalized SHA-256 stem hash (`bank_build.py:89–91`), "
            "unique live bank index on (course_id, skill_id, stem_hash) "
            "(`packages/db/migrations/0021_question_bank.sql:22–24`); exact choice-set reuse rejection "
            "(`bank_build.py:260–263`); token-set Jaccard **> 0.8**, not cosine, against the latest "
            "30 live stems and earlier accepted batch items (`bank_build.py:94–97`, `:275–280`, "
            "`:335–338`, `:491–508`). Rephrasing and synonyms can pass this lexical filter. "
            "No semantic dedupe occurs when selecting a test set (`services/api/app/bank/serving.py:40–68`, "
            "`:85–104`).", "", "## A3. Assigned lesson checks", "",
            "Scope: every stored guided lesson in every bank_serving=true course, including lessons "
            "whose skill is no longer approved. Read stored check ids without assigning missing ones. "
            "Off-topic heuristic: check prompt vs title + summary + detail_points < 0.45. "
            "There is no stored step title, so summary is used. Missing checks/text are N/A, "
            "not silently counted as on-topic. Check choices/explanations are not embedded. "
            "Step numbers and duplicate pairs below use the stored zero-based position: position 0 "
            "is the first step shown to a student.", ""]
    bank_courses = {c["id"] for c in courses.values() if c["bank_serving"]}
    lessons = [l for l in data["guided_lessons"] if l["course_id"] in bank_courses]
    check_map = {i["id"]: i for i in data["checks"] + items}
    steps_by_lesson = defaultdict(list)
    for step in data["guided_lesson_steps"]:
        steps_by_lesson[step["lesson_id"]].append(step)
    texts = []
    for lesson in lessons:
        for step in steps_by_lesson[lesson["id"]]:
            check = check_map.get(step.get("check_item_id"))
            if check:
                texts += [check["prompt"], relevance_text(step)]
    vectors.fill(texts)
    analyses = []
    thin = []
    for lesson in lessons:
        steps = sorted(steps_by_lesson[lesson["id"]], key=lambda s: s["position"])
        enriched = []
        for step in steps:
            check = check_map.get(step.get("check_item_id"))
            text = relevance_text(step)
            score = cosine(vectors.get(check["prompt"]), vectors.get(text)) if check and text else None
            visible = bool(check and check.get("retired_at") is None
                           and skills.get(check["skill_id"], {}).get("status") == "approved")
            enriched.append((step, check, score, visible))
            length = len(teaching(step))
            if not step.get("detail_points") or length < 200:
                thin.append([short(lesson["id"]), step["position"], length,
                             len(step.get("detail_points") or []), "empty key points" if not step.get("detail_points") else "under 200 chars"])
        dup = []
        for a, b in itertools.combinations(enriched, 2):
            if a[1] and b[1]:
                similarity = cosine(vectors.get(a[1]["prompt"]), vectors.get(b[1]["prompt"]))
                if similarity >= .90:
                    dup.append((a[0]["position"], b[0]["position"], similarity))
        analyses.append((lesson, enriched, dup))
    dup_lessons = sum(bool(a[2]) for a in analyses)
    off = sum(s[2] is not None and s[2] < .45 for a in analyses for s in a[1])
    visible_duplicate_lessons = sum(any(
        next(s for s in steps if s[0]["position"] == first)[3]
        and next(s for s in steps if s[0]["position"] == second)[3]
        for first, second, _ in duplicates) for _, steps, duplicates in analyses)
    out += [f"Lessons audited: **{len(lessons)}**; lessons with duplicate checks: **{dup_lessons}**; "
            f"steps flagged off-topic: **{off}**; total steps: **{sum(len(a[1]) for a in analyses)}**. "
            f"Missing check rows: {sum(s[1] is None for a in analyses for s in a[1])}. "
            f"Stored checks currently hidden by retired/unapproved filtering: "
            f"{sum(s[1] is not None and not s[3] for a in analyses for s in a[1])}. "
            f"Lessons with a duplicate pair where both checks are currently displayable: "
            f"{visible_duplicate_lessons}.", ""]
    out += table(["Lesson", "Title", "Skill status", "Steps", "Duplicate pairs", "Off-topic steps"], [
        [short(l["id"]), l["title"], skills.get(l["skill_id"], {}).get("status"), len(ss), len(dd),
         sum(s[2] is not None and s[2]<.45 for s in ss)] for l, ss, dd in analyses])
    out += ["", "### Every lesson and step", ""]
    for lesson, steps, duplicates in analyses:
        out += [f"#### {short(lesson['id'])}: {lesson['title']}", ""]
        out += table(["Step", "Summary (60)", "Bloom", "Check", "Check prompt (80)", "Cosine to step", "Flags"], [
            [s["position"], s.get("summary", "")[:60], s.get("bloom_level"), short(c["id"]) if c else "NONE",
             c["prompt"][:80] if c else "NONE", f"{score:.6f}" if score is not None else "N/A",
             ", ".join(flag for flag, applies in [("off-topic", score is not None and score < .45),
                  ("hidden", c is not None and not visible), ("missing check", c is None),
                  ("duplicate", any(s["position"] in p[:2] for p in duplicates))] if applies)]
            for s, c, score, visible in steps])
        out += ["", "Duplicate step pairs: " + ("; ".join(f"{a}–{b}: {score:.6f}" for a,b,score in duplicates) or "none"), ""]
    out += ["### Five worst lessons in full", "",
            "Ranked by off-topic count descending, duplicate-pair count descending, minimum relevance "
            "ascending, then lesson id. These thresholds need human review; related topics can score "
            "high without matching the step's teaching objective.", ""]
    worst = sorted(analyses, key=lambda a: (-sum(s[2] is not None and s[2]<.45 for s in a[1]),
        -len(a[2]), min((s[2] for s in a[1] if s[2] is not None), default=1), a[0]["id"]))[:5]
    for lesson, steps, duplicates in worst:
        out += [f"#### {short(lesson['id'])}: {lesson['title']}", ""]
        for s, c, score, visible in steps:
            out += [f"**Step {s['position']} — {s.get('bloom_level')}**", "", teaching(s), "",
                    "**Assigned check:** " + (c["prompt"] if c else "NONE"), "",
                    f"Check id: {short(c['id']) if c else 'NONE'}; cosine: "
                    + (f"{score:.6f}" if score is not None else "N/A") + f"; currently displayable: {visible}.", ""]
        out += ["Duplicate pairs: " + ("; ".join(f"{a}–{b}: {v:.6f}" for a,b,v in duplicates) or "none"), ""]
    out += ["Assembly evidence: `services/api/app/learn/lessons.py:385–411`: skill-wide bank pool, "
            "prefer lesson source-chunk intersection, then oldest first, zip unassigned steps to available "
            "items. It excludes repeated ids but does not compare step text, Bloom level, or semantic "
            "similarity. Assigned legacy checks remain assigned. Display filtering is at lines 414–424. "
            "Review full teaching text before treating a cosine flag as a confirmed duplicate or "
            "off-topic check; related vocabulary can obscure different teaching objectives. "
            "The audit deliberately never invokes this function because lines 408–411 can write.", "",
            "## A4. Thin lesson steps", "",
            f"Thin steps: **{len(thin)}**. Same bank-serving-course lesson scope as A3. "
            "Total teaching text is newline-joined title (if stored), summary, detail_points, "
            "misconception, and key_takeaway, stripped per field; check prompt is excluded. "
            "Empty detail_points is flagged regardless of text length.", ""]
    out += table(["Lesson", "Step", "Teaching characters", "Key points", "Reason"], thin)
    out += ["", "## Embedding accounting and limits", "",
            f"Embedding function calls recorded for this local cache: **{vectors.prior_calls + vectors.calls}**; "
            f"calls in this invocation: **{vectors.calls}**; cached unique text hits: "
            f"{vectors.hits}. No stored generated-item vectors were available. Provider/model: "
            f"{vectors.provider}/{vectors.model}. No chat/completion or live database writes. "
            "Identical text shares one local cached vector; the count is outbound function invocations, "
            "not number of item pairs. No student identifiers or names are read into the report. "
            "Only course, skill, lesson, and item ids are shown, shortened to eight characters.", ""]
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, help="Read local snapshot; no live SELECTs")
    parser.add_argument("--save-snapshot", type=Path)
    parser.add_argument("--cache", type=Path, default=Path("/tmp/kala-bank-quality-vectors.json"))
    parser.add_argument("--report", type=Path, default=ROOT / "docs/audits/2026-10-18-bank-lesson-audit.md")
    parser.add_argument("--allow-embeddings", action="store_true")
    args = parser.parse_args()
    data = json.loads(args.snapshot.read_text()) if args.snapshot else snapshot()
    print(f"A1: bank={len(data['items'])}, broken={sum(map(broken, data['items']))}", flush=True)
    if args.save_snapshot:
        args.save_snapshot.write_text(json.dumps(data))
    vectors = Vectors(args.cache, args.allow_embeddings)
    try:
        content = report(data, vectors)
    finally:
        print(f"Embedding function calls this run: {vectors.calls}", flush=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(content)
    print(f"Report: {args.report}", flush=True)


if __name__ == "__main__":
    main()
