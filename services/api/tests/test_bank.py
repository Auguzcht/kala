import pytest
from fastapi import HTTPException

from app.bank import kick as kick_module
from app.deps import CurrentUser
from app.routers import bank as bank_router


def test_kick_bank_debounces_second_call(monkeypatch):
    updates = []
    invokes = []
    def update(*args, **kwargs):
        result = [{"id": "c"}] if not updates else []
        updates.append(1)
        return result
    monkeypatch.setattr(kick_module.db, "update", update)
    monkeypatch.setattr(kick_module, "get_settings", lambda: type("S", (), {"worker_function_arn": "arn", "aws_region": "ap-southeast-1"})())
    class Lambda:
        def invoke(self, **kwargs): invokes.append(kwargs)
    monkeypatch.setattr(kick_module.boto3, "client", lambda *args, **kwargs: Lambda())
    assert kick_module.kick_bank("c", "status") is True
    assert kick_module.kick_bank("c", "status") is False
    assert len(invokes) == 1


def test_student_status_hides_last_error_and_other_course_is_404(monkeypatch):
    user = CurrentUser("u", "i", "student")
    monkeypatch.setattr(bank_router.db, "select", lambda table, params: (
        [{"id": "c", "institution_id": "i"}] if table == "courses" else
        ([{"user_id": "u"}] if table == "enrollments" else
         [{"skill_id": "s", "status": "error", "mcq_ready": 0, "mcq_target": 5, "depth": 2, "last_error": "secret"}])
    ))
    monkeypatch.setattr(bank_router, "kick_bank", lambda *args: False)
    result = bank_router.bank_status("c", user)
    assert "lastError" not in result["skills"][0]
    assert result["skills"][0]["usable"] is False

    def other_course(table, params):
        if table == "courses":
            return [{"id": "c", "institution_id": "i"}]
        return []
    monkeypatch.setattr(bank_router.db, "select", other_course)
    with pytest.raises(HTTPException) as exc:
        bank_router.bank_status("c", user)
    assert exc.value.status_code == 404
