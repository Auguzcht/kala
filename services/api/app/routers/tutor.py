"""AI tutor. De-identifies context, retrieves course material, answers via the
tiered router. Never returns raw answers to graded assessments."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.ai import rag, router as model_router
from app.ai.deidentify import safe_context
from app.deps import CurrentUser, get_current_user

router = APIRouter(prefix="/tutor", tags=["tutor"])

_SYSTEM = "You are Kala, a study tutor. Teach and give hints. Never reveal answers to graded work."


class Ask(BaseModel):
    course_id: str
    question: str


@router.post("/ask")
def ask(body: Ask, user: CurrentUser = Depends(get_current_user)):
    chunks = rag.retrieve(
        institution_id=user.institution_id, course_id=body.course_id, query=body.question,
    )
    context = "\n".join(c.get("chunk_text", "") for c in chunks)
    prompt = safe_context(user, f"Course context:\n{context}\n\nQuestion: {body.question}")
    return {"answer": model_router.answer(system=_SYSTEM, user_text=prompt)}
