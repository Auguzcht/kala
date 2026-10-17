"""Best-effort worker wake-up for bank progress."""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta

import boto3

from app.config import get_settings
from app.db import supabase as db

logger = logging.getLogger("kala.api.bank")


def kick_bank(course_id: str, trigger: str) -> bool:
    now = datetime.now(UTC)
    cutoff = now - timedelta(seconds=60)
    try:
        rows = db.update("courses", {"id": f"eq.{course_id}",
                                      "or": f"(bank_kicked_at.is.null,bank_kicked_at.lt.{cutoff.isoformat()})"},
                         {"bank_kicked_at": now.isoformat()})
    except Exception as exc:  # noqa: BLE001 — wake-up is never request-critical
        logger.warning("bank kick debounce update failed course_id=%s error=%s", course_id, exc)
        return False
    if not rows:
        return False
    try:
        settings = get_settings()
        if not settings.worker_function_arn:
            raise RuntimeError("WORKER_FUNCTION_ARN is not configured")
        boto3.client("lambda", region_name=settings.aws_region).invoke(
            FunctionName=settings.worker_function_arn, InvocationType="Event",
            Payload=json.dumps({"trigger": trigger, "courseId": course_id, "chainDepth": 0}).encode(),
        )
    except Exception as exc:  # noqa: BLE001 — a kick never fails its caller
        logger.warning("bank kick invoke failed course_id=%s trigger=%s error=%s", course_id, trigger, exc)
    return True


def kick_lesson_checks(course_id: str, lesson_id: str) -> bool:
    """Wake one lesson's resumable checker at most once per minute."""
    now = datetime.now(UTC)
    cutoff = now - timedelta(seconds=60)
    key = f"lesson_check_kick:{lesson_id}"
    try:
        filters = {
            "key": f"eq.{key}",
            # Like kick_bank's conditional course timestamp update, this is a
            # single atomic update. It also refuses to kick during a live job lease.
            "and": (
                f"(or(updated_at.is.null,updated_at.lt.{cutoff.isoformat()}),"
                f"or(value->>lease_until.is.null,value->>lease_until.lt.{now.isoformat()}))"
            ),
        }
        claimed = db.update("worker_state", filters, {
            "updated_at": now.isoformat(), "value": {"lease_until": None},
        })
        if not claimed:
            # The first request creates the per-lesson row and owns its initial
            # kick. A concurrent insert loses on worker_state.key's primary key.
            try:
                claimed = db.insert("worker_state", [{
                    "key": key, "value": {"lease_until": None},
                    "updated_at": now.isoformat(),
                }])
            except Exception as exc:  # noqa: BLE001 - concurrent first insert is expected
                if getattr(getattr(exc, "response", None), "status_code", None) == 409:
                    return False
                raise
        if not claimed:
            return False
        settings = get_settings()
        if not settings.worker_function_arn:
            raise RuntimeError("WORKER_FUNCTION_ARN is not configured")
        boto3.client("lambda", region_name=settings.aws_region).invoke(
            FunctionName=settings.worker_function_arn, InvocationType="Event",
            Payload=json.dumps({"trigger": "lesson_checks", "courseId": course_id,
                                "lessonId": lesson_id, "chainDepth": 0}).encode(),
        )
        return True
    except Exception as exc:  # noqa: BLE001 - check assignment never fails lesson display
        logger.warning("lesson check kick failed course_id=%s lesson_id=%s error=%s",
                       course_id, lesson_id, exc)
        return False
