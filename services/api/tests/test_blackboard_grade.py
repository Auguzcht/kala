from unittest.mock import patch

from app.config import Settings
from app.lms.blackboard import BlackboardConnector


class Response:
    def raise_for_status(self):
        pass


def test_post_grade_patches_blackboard_column_user():
    settings = Settings(
        LMS_REST_BASE_URL="https://learn.example/learn/api/public/v1",
        LMS_VERIFY_TLS=False,
    )
    with patch("app.lms.blackboard.get_settings", return_value=settings), patch(
        "app.lms.blackboard.httpx.patch", return_value=Response()
    ) as patch_request:
        connector = BlackboardConnector()
        connector._headers = lambda: {"Authorization": "Bearer test"}
        connector.post_grade("_4_1", "_8_1", "_6_1", 85.0)

    assert patch_request.call_args.args[0].endswith(
        "/courses/_4_1/gradebook/columns/_8_1/users/_6_1"
    )
    assert patch_request.call_args.kwargs["json"] == {"score": 85.0}
    assert patch_request.call_args.kwargs["verify"] is False