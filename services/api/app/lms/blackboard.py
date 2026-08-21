"""Blackboard (Anthology) connector over the Learn REST API. Uses an OAuth 2
client-credentials token from the Learn token endpoint. Methods are partial;
fill in the response mapping against your instance's REST schema.

For roster and grade passback you may also use LTI NRPS and AGS from the launch
claims; both are valid. REST is the simpler data pipe for the pilot."""
from __future__ import annotations

import time
from urllib.parse import quote

import httpx

from app.config import get_settings
from app.lms.base import LMSConnector


class BlackboardConnector(LMSConnector):
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
            auth=(s.lms_rest_client_id, s.lms_rest_client_secret),
            verify=s.lms_verify_tls,
            timeout=15.0,
        )
        resp.raise_for_status()
        body = resp.json()
        self._token = body["access_token"]
        self._expires_at = time.time() + int(body.get("expires_in", 3600))
        return self._token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._get_token()}"}

    def resolve_course_ref(self, external_id: str) -> str:
        s = get_settings()
        resp = httpx.get(
            f"{s.lms_rest_base_url}/courses/externalId:{quote(external_id, safe='')}",
            headers=self._headers(),
            verify=s.lms_verify_tls,
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json()["id"]

    def get_roster(self, course_ref: str) -> list[dict]:
        s = get_settings()
        resp = httpx.get(
            f"{s.lms_rest_base_url}/courses/{course_ref}/users",
            headers=self._headers(),
            params={
                "expand": "users",
                "fields": "userId,courseRoleId,user.id,user.name,user.contact.email",
            },
            verify=s.lms_verify_tls,
            timeout=15.0,
        )
        resp.raise_for_status()

        memberships = resp.json().get("results", [])
        roster = []
        for membership in memberships:
            user = membership.get("user", {})
            name = user.get("name", {})
            display_name = name.get("preferredDisplayName") or " ".join(
                part for part in (name.get("given"), name.get("family")) if part
            )
            roster.append({
                "lms_user_id": membership["userId"],
                "role": membership.get("courseRoleId"),
                "name": display_name,
                "email": user.get("contact", {}).get("email"),
            })
        return roster

    def get_content(self, course_ref: str) -> list[dict]:
        s = get_settings()
        headers = self._headers()

        def fetch_children(parent_id: str | None = None) -> list[dict]:
            path = f"{s.lms_rest_base_url}/courses/{course_ref}/contents"
            if parent_id:
                path += f"/{parent_id}/children"
            resp = httpx.get(
                path,
                headers=headers,
                verify=s.lms_verify_tls,
                timeout=15.0,
            )
            resp.raise_for_status()
            return resp.json().get("results", [])

        def flatten(items: list[dict]) -> list[dict]:
            content = []
            for item in items:
                handler = item.get("contentHandler") or {}
                content.append({
                    "lms_content_id": item["id"],
                    "title": item.get("title") or "Untitled",
                    "body_or_description": item.get("body") or item.get("description") or "",
                    "content_type": handler.get("id"),
                    "parent_id": item.get("parentId"),
                })
                if item.get("hasChildren"):
                    content.extend(flatten(fetch_children(item["id"])))
            return content

        return flatten(fetch_children())

    def get_assessments(self, course_ref: str) -> list[dict]:
        s = get_settings()
        resp = httpx.get(
            f"{s.lms_rest_base_url}/courses/{course_ref}/gradebook/columns",
            headers=self._headers(),
            params={
                "fields": "id,name,displayName,score.possible,grading.type",
            },
            verify=s.lms_verify_tls,
            timeout=15.0,
        )
        resp.raise_for_status()

        return [{
            "lms_column_id": column["id"],
            "name": column.get("name") or column.get("displayName") or "Untitled",
            "points_possible": (column.get("score") or {}).get("possible"),
            "grading_type": (column.get("grading") or {}).get("type"),
        } for column in resp.json().get("results", [])]

    def post_grade(self, course_ref: str, column_id: str, user_ref: str, score: float) -> None:
        s = get_settings()
        resp = httpx.patch(
            f"{s.lms_rest_base_url}/courses/{course_ref}/gradebook/columns/{column_id}/users/{user_ref}",
            headers=self._headers(),
            json={"score": score},
            verify=s.lms_verify_tls,
            timeout=15.0,
        )
        resp.raise_for_status()
