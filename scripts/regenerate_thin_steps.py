#!/usr/bin/env python3
"""List lesson steps with fewer than two key points or under 200 chars."""
from __future__ import annotations

from lesson_check_tools import select_all


def main() -> None:
    lessons = select_all("guided_lessons", {"select": "id,course_id,title"})
    thin = []
    for lesson in lessons:
        steps = select_all("guided_lesson_steps", {
            "lesson_id": f"eq.{lesson['id']}",
            "select": "id,position,summary,detail_points,misconception,key_takeaway",
        })
        for step in steps:
            points = step.get("detail_points") or []
            teaching = "\n".join(str(value).strip() for value in
                                  [step.get("summary"), *points, step.get("misconception"), step.get("key_takeaway")]
                                  if value and str(value).strip())
            if len(points) < 2 or len(teaching) < 200:
                thin.append((lesson, step, len(points), len(teaching)))
    print(f"Thin steps: {len(thin)}")
    for lesson, step, point_count, length in thin:
        print(f"lesson={lesson['id']} course={lesson['course_id']} step={step['id']} position={step['position']} "
              f"points={point_count} teaching_chars={length} summary={step.get('summary','')[:100]}")
    print("Mode: DRY RUN (read-only)")


if __name__ == "__main__":
    main()
