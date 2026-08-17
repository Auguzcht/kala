"""Blackboard (Anthology) connector over the Learn REST API. Uses an OAuth 2
client-credentials token from the Learn token endpoint. Methods are partial;
fill in the response mapping against your instance's REST schema.

For roster and grade passback you may also use LTI NRPS and AGS from the launch
claims; both are valid. REST is the simpler data pipe for the pilot."""
from __future__ import annotations

import time

import httpx

from app.config import get_settings


class BlackboardConnector:
    def __init__(self) -> None:
        self._token: str | None = None
        self._expires_at: float = 0.0

    def _get_token(self) -> str:
        s = get_settings()
        if self._token and time.time() < self._expires_at - 30:
            return self._token
        # Learn REST uses application key/secret via client_credentials.
        resp = httpx.post(
            s.lti_auth_token_url,
            data={"grant_type": "client_credentials"},
            auth=(s.lti_client_id, ""),  # set the REST secret in your secrets bundle
            timeout=15.0,
        )
        resp.raise_for_status()
        body = resp.json()
        self._token = body["access_token"]
        self._expires_at = time.time() + int(body.get("expires_in", 3600))
        return self._token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._get_token()}"}

    def get_roster(self, course_ref: str) -> list[dict]:
        # GET /learn/api/public/v1/courses/{courseId}/users
        return []  # TODO: map to [{lms_user_id, role, name, email}]

    def get_content(self, course_ref: str) -> list[dict]:
        # GET /learn/api/public/v1/courses/{courseId}/contents
        return []  # TODO: map to chunkable content items

    def get_grades(self, course_ref: str) -> list[dict]:
        # GET /learn/api/public/v1/courses/{courseId}/gradebook/columns...
        return []

    def post_grade(self, course_ref: str, user_ref: str, score: float) -> None:
        # PATCH gradebook column attempt, or use LTI AGS from the launch.
        return None
