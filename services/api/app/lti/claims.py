"""LTI 1.3 claim URIs and role mapping. Keeping these in one place avoids
scattering magic strings through the launch handler."""
from __future__ import annotations

# Standard LTI 1.3 message claims
MESSAGE_TYPE = "https://purl.imsglobal.org/spec/lti/claim/message_type"
VERSION = "https://purl.imsglobal.org/spec/lti/claim/version"
DEPLOYMENT_ID = "https://purl.imsglobal.org/spec/lti/claim/deployment_id"
ROLES = "https://purl.imsglobal.org/spec/lti/claim/roles"
CONTEXT = "https://purl.imsglobal.org/spec/lti/claim/context"
RESOURCE_LINK = "https://purl.imsglobal.org/spec/lti/claim/resource_link"
CUSTOM = "https://purl.imsglobal.org/spec/lti/claim/custom"
TARGET_LINK_URI = "https://purl.imsglobal.org/spec/lti/claim/target_link_uri"

EXPECTED_MESSAGE_TYPE = "LtiResourceLinkRequest"
EXPECTED_VERSION = "1.3.0"

# Role URI fragments
_ROLE_ADMIN = "#Administrator"
_ROLE_INSTRUCTOR = "#Instructor"
_ROLE_LEARNER = "#Learner"


def map_role(role_uris: list[str]) -> str:
    """Map the LTI roles claim to a Kala app_role. Admin and instructor win
    over learner if multiple are present."""
    joined = " ".join(role_uris or [])
    if _ROLE_ADMIN in joined:
        return "admin"
    if _ROLE_INSTRUCTOR in joined:
        return "instructor"
    if _ROLE_LEARNER in joined:
        return "student"
    return "student"  # safest default: least privilege


def extract_context(claims: dict) -> dict:
    ctx = claims.get(CONTEXT) or {}
    return {
        "lti_context_id": ctx.get("id"),
        "lms_course_external_id": ctx.get("label"),
        "title": ctx.get("title") or ctx.get("label") or "Course",
    }
