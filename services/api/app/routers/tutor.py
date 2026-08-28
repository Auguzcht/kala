"""AI tutor (free-form chat mode). De-identifies context, retrieves course
material, answers via the tiered router. Never returns raw answers to graded
assessments.

Two tutor modes exist in the product: this free-form chat, and the persistent
step-by-step walkthrough (see routers/lessons.py, the guided lesson). This
module owns chat. The optional `style` supports the follow-up chips from the
target design ("Explain like I'm 5", "More detail") by adjusting the framing
of the SAME grounded answer, so a chip is a cheap re-render, not a new
retrieval contract.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.ai import rag, router as model_router
from app.ai.deidentify import safe_context
from app.deps import CurrentUser, get_current_user

router = APIRouter(prefix="/tutor", tags=["tutor"])

_SYSTEM = "You are Kala, a study tutor. Teach and give hints. Never reveal answers to graded work."

# Style modifiers for the follow-up chips. Appended to the system prompt so the
# grounding and safety rules are unchanged; only the register shifts.
_STYLE_HINTS: dict[str, str] = {
    "default": "",
    "eli5": " Explain simply, as if to a beginner, using a short everyday analogy. Assume no prior knowledge.",
    "detail": " Go deeper: add the underlying reasoning and one concrete example, still grounded only in the course context.",
}


class Ask(BaseModel):
    course_id: str
    question: str
    style: Literal["default", "eli5", "detail"] = "default"


@router.post("/ask")
def ask(body: Ask, user: CurrentUser = Depends(get_current_user)):
    chunks = rag.retrieve(
        institution_id=user.institution_id, course_id=body.course_id, query=body.question,
    )
    context = "\n".join(c.get("chunk_text", "") for c in chunks)
    prompt = safe_context(user, f"Course context:\n{context}\n\nQuestion: {body.question}")
    system = _SYSTEM + _STYLE_HINTS.get(body.style, "")
    return {"answer": model_router.answer(system=system, user_text=prompt)}
