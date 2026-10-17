#!/usr/bin/env python3
"""Compare stored and similarity-based lesson checks; dry-run unless confirmed."""
from __future__ import annotations

import argparse

from lesson_check_tools import VectorCache, current_and_new_assignments, lesson_and_steps, select_all
from app.db import supabase as db
from app.jobs.assign_lesson_checks import run as assign_lesson_checks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--course-id", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm")
    parser.add_argument("--cache", default="/tmp/kala-bank-quality-vectors.json")
    args = parser.parse_args()
    if args.apply and args.confirm != args.course_id:
        parser.error("--apply requires --confirm <same course-id>")
    lessons = select_all("guided_lessons", {
        "course_id": f"eq.{args.course_id}",
        "select": "id,course_id,skill_id,title,status",
    })
    vectors = VectorCache(args.cache)
    for lesson in lessons:
        _, steps = lesson_and_steps(lesson)
        items, old, _ = current_and_new_assignments(lesson, steps, vectors)
        # Preview a fresh full assignment so existing ids do not constrain the
        # suggested mapping. The apply path clears only check_item_id values.
        preview_steps = [{**step, "check_item_id": None} for step in steps]
        from app.lesson_matching import assign_matches
        new = assign_matches(preview_steps, items)
        item_by_id = {item["id"]: item for item in items}
        print(f"\nLESSON {lesson['id']} — {lesson.get('title') or ''}")
        for step in steps:
            previous, old_score = old.get(step["id"], (None, None))
            match = new.get(step["id"])
            proposed, new_score = (item_by_id[match[0]], match[1]) if match else (None, None)
            print(f"step {step['position']}: {step.get('summary','')[:70]}")
            print(f"  old: {previous.get('prompt','')[:70] if previous else 'NONE'}; score={old_score if old_score is not None else '—'}")
            print(f"  new: {proposed.get('prompt','')[:70] if proposed else 'CHECK COMING'}; score={new_score if new_score is not None else '—'}")
    if args.apply:
        for lesson in lessons:
            steps = select_all("guided_lesson_steps", {
                "lesson_id": f"eq.{lesson['id']}", "select": "id,check_item_id",
            })
            for step in steps:
                if step.get("check_item_id"):
                    db.update("guided_lesson_steps", {"id": f"eq.{step['id']}"},
                              {"check_item_id": None})
            assign_lesson_checks(lesson_id=lesson["id"])
    print(f"\nEmbedding calls this run: {vectors.calls}")
    print("Mode: APPLY" if args.apply else "Mode: DRY RUN")


if __name__ == "__main__":
    main()
