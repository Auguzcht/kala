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
