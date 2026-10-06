import json

from app import handler as handler_module
from app import rag


def test_real_handler_targeted_bank_chain_uses_configured_chain_max(monkeypatch):
    invoked = []

    def select(table, params):
        if table == "courses":
            return [{"id": "course-1", "institution_id": "institution-1"}]
        if table == "skills":
            return [{"id": "skill-1", "name": "Cloud elasticity", "bloom_level": "understand", "embedding": "[1.0,0.0]"}]
        if table == "skill_bank_state":
            return [{"institution_id": "institution-1", "course_id": "course-1", "skill_id": "skill-1",
                     "depth": 1, "mcq_ready": 0, "mcq_target": 5, "consecutive_failures": 0}]
        if table in {"enrollments", "evidence_events", "generated_items", "item_exposures", "content_items"}:
            return []
        raise AssertionError(f"unexpected select: {table}")

    monkeypatch.setattr(handler_module.db, "select", select)
    monkeypatch.setattr(handler_module.db, "upsert", lambda table, rows, on_conflict: rows)
    monkeypatch.setattr(handler_module.db, "update", lambda table, filters, values: [])
    monkeypatch.setattr(rag, "retrieve_embedding", lambda **kwargs: [{"id": "chunk-1", "chunk_text": "x" * 1200, "similarity": 0.9}])
    monkeypatch.setenv("WORKER_FUNCTION_ARN", "arn:aws:lambda:ap-southeast-1:123:function:worker")
    handler_module.get_settings.cache_clear()

    class LambdaClient:
        def invoke(self, **kwargs):
            invoked.append(kwargs)
            return {"StatusCode": 202}

    monkeypatch.setattr("boto3.client", lambda name: LambdaClient())
    result = handler_module.handler({"trigger": "bank", "courseId": "course-1", "chainDepth": 0}, None)

    assert result["ok"] is True
    assert invoked
    assert json.loads(invoked[0]["Payload"]) == {"trigger": "bank", "courseId": "course-1", "chainDepth": 1}
    handler_module.get_settings.cache_clear()


def test_real_handler_chain_depth_stops_at_chain_max(monkeypatch):
    invoked = []

    def select(table, params):
        if table == "courses":
            return [{"id": "course-1", "institution_id": "institution-1"}]
        if table == "skills":
            return [{"id": "skill-1", "name": "Cloud elasticity", "bloom_level": "understand", "embedding": "[1.0,0.0]"}]
        if table == "skill_bank_state":
            return [{"institution_id": "institution-1", "course_id": "course-1", "skill_id": "skill-1",
                     "depth": 1, "mcq_ready": 0, "mcq_target": 5, "consecutive_failures": 0}]
        if table in {"enrollments", "evidence_events", "generated_items", "item_exposures", "content_items"}:
            return []
        raise AssertionError(f"unexpected select: {table}")

    monkeypatch.setattr(handler_module.db, "select", select)
    monkeypatch.setattr(handler_module.db, "upsert", lambda table, rows, on_conflict: rows)
    monkeypatch.setattr(handler_module.db, "update", lambda table, filters, values: [])
    monkeypatch.setattr(rag, "retrieve_embedding", lambda **kwargs: [{"id": "chunk-1", "chunk_text": "x" * 1200, "similarity": 0.9}])
    monkeypatch.setenv("WORKER_FUNCTION_ARN", "arn:aws:lambda:ap-southeast-1:123:function:worker")
    handler_module.get_settings.cache_clear()

    class LambdaClient:
        def invoke(self, **kwargs):
            invoked.append(kwargs)
            return {"StatusCode": 202}

    monkeypatch.setattr("boto3.client", lambda name: LambdaClient())
    event = {"trigger": "bank", "courseId": "course-1", "chainDepth": 0}
    for _ in range(handler_module.CHAIN_MAX + 1):
        handler_module.handler(event, None)
        if not invoked:
            break
        event = json.loads(invoked[-1]["Payload"])

    assert len(invoked) == handler_module.CHAIN_MAX
    assert json.loads(invoked[-1]["Payload"])["chainDepth"] == handler_module.CHAIN_MAX
    handler_module.get_settings.cache_clear()
