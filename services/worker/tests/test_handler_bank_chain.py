import json
from types import SimpleNamespace

from app import handler as handler_module


def test_chain_starts_continuation_when_work_remains(monkeypatch):
    invoked = []
    monkeypatch.setenv("WORKER_FUNCTION_ARN", "arn:aws:lambda:ap-southeast-1:123:function:worker")
    handler_module.get_settings.cache_clear()

    class LambdaClient:
        def invoke(self, **kwargs):
            invoked.append(kwargs)
            return {"StatusCode": 202}

    monkeypatch.setattr("boto3.client", lambda name: LambdaClient())
    handler_module._maybe_chain("course", {"remaining": True, "budget_exhausted": True}, 0, {}, "propose")
    assert json.loads(invoked[0]["Payload"]) == {
        "trigger": "propose", "courseId": "course", "chainDepth": 1,
    }
    handler_module.get_settings.cache_clear()


def test_permanent_error_and_throttle_do_not_chain(monkeypatch):
    invoked = []
    monkeypatch.setenv("WORKER_FUNCTION_ARN", "arn:aws:lambda:ap-southeast-1:123:function:worker")
    handler_module.get_settings.cache_clear()

    class LambdaClient:
        def invoke(self, **kwargs):
            invoked.append(kwargs)
            return {"StatusCode": 202}

    monkeypatch.setattr("boto3.client", lambda name: LambdaClient())
    handler_module._maybe_chain("course", {"remaining": True, "permanent_error": True,
        "error_status": 400, "error_reason": "invalid reasoning"}, 0, {}, "propose")
    handler_module._maybe_chain("course", {"remaining": True, "rate_limited": True}, 0, {}, "propose")
    assert invoked == []
    handler_module.get_settings.cache_clear()


def test_chain_depth_limit_stops(monkeypatch, caplog):
    invoked = []
    monkeypatch.setenv("WORKER_FUNCTION_ARN", "arn:aws:lambda:ap-southeast-1:123:function:worker")
    handler_module.get_settings.cache_clear()

    class LambdaClient:
        def invoke(self, **kwargs):
            invoked.append(kwargs)
            return {"StatusCode": 202}

    monkeypatch.setattr("boto3.client", lambda name: LambdaClient())
    with caplog.at_level("WARNING", logger="kala.worker"):
        handler_module._maybe_chain("course", {"remaining": True}, handler_module.CHAIN_MAX, {}, "bank")
    assert invoked == []
    assert "reason=depth_limit" in caplog.text
    assert "handing off to schedule" in caplog.text
    assert handler_module.CHAIN_MAX == 12
    handler_module.get_settings.cache_clear()


def test_depth_limited_refresh_resumes_on_next_scheduled_run_with_bank_build(monkeypatch):
    proposer_calls = []
    bank_calls = []
    worker_state = [
        {"key": "proposer:course-a:module-1", "value": {
            "windows_completed": 2, "windows_total": 4, "content_freshness": "same",
        }},
        {"key": "proposer:course-b:module-2", "value": {
            "windows_completed": 4, "windows_total": 4, "content_freshness": "same",
        }},
    ]

    monkeypatch.setattr(handler_module.db, "select", lambda table, params: worker_state if table == "worker_state" else [])
    for name in ("reconcile_mastery", "ingest_walk", "embed_backfill", "embed_bank_items", "readiness_snapshot",
                 "item_generation", "tag_recompute"):
        monkeypatch.setattr(handler_module, name, SimpleNamespace(run=lambda **kwargs: {}))
    monkeypatch.setattr(handler_module.skill_proposer, "run",
                        lambda **kwargs: proposer_calls.append(kwargs) or {"remaining": False})
    monkeypatch.setattr(handler_module.bank_build, "run",
                        lambda **kwargs: bank_calls.append(kwargs) or {"remaining": True})

    # Simulate chain depth 12 handing off its 2/4 cursor. The next invocation
    # is the scheduled event, with no trigger or course id from a new click.
    handler_module._maybe_chain("course-a", {"remaining": True, "modulesRemaining": 1},
                                handler_module.CHAIN_MAX, {}, "propose")
    result = handler_module.handler({}, None)

    assert result["ok"] is True
    assert len(proposer_calls) == 1
    assert proposer_calls[0]["course_id"] == "course-a"
    assert len(bank_calls) == 1
    assert bank_calls[0]["institution_id"] is None
    assert bank_calls[0]["remaining_seconds"] > 0


def test_scheduled_cursor_query_selects_only_incomplete_windows(monkeypatch):
    captured = {}
    monkeypatch.setattr(handler_module.db, "select", lambda table, params:
                        captured.update({"table": table, "params": params}) or [])
    assert handler_module._incomplete_proposal_courses() == []
    assert captured["table"] == "worker_state"
    assert captured["params"]["key"] == "like.proposer:%"
