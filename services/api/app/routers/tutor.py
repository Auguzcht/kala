"""AI tutor (free-form chat mode). De-identifies context, retrieves course
material, answers via the tiered router. Never returns raw answers to graded
assessments.

Two tutor modes exist in the product: this free-form chat, and the persistent
step-by-step walkthrough (see routers/lessons.py, the guided lesson). This
module owns chat. The optional `style` supports the follow-up chips from the
target design ("Explain like I'm 5", "More detail") by adjusting the framing
of the SAME grounded answer, so a chip is a cheap re-render, not a new
retrieval contract.

AI overhaul Stage 2 (docs/AI_OVERHAUL_TODO.md): the tutor gained real
conversation persistence. Previously /ask was fully stateless — no
conversation_id, nothing stored, each question independent, gone on
refresh. Conversations now live in tutor_conversations/tutor_messages
(migration 0010). /ask still works exactly as before if you never pass a
conversation_id, it just also now supports building on a real thread.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.ai import rag, router as model_router
from app.ai.deidentify import safe_context
from app.db import supabase as db
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

# How many prior messages feed a follow-up as conversation context. A cap,
# not the full thread: an unbounded history would grow every prompt's token
# cost with every turn, for a study-tutor chat the last few exchanges are
# what "remembers what we were just talking about" actually needs. Tunable
# without a migration if it turns out too short/long in practice.
_HISTORY_TURNS = 10


def _owned_conversation(conversation_id: str, user: CurrentUser) -> dict:
    """Fetch a conversation, 404 if it doesn't belong to this user. This is
    client-supplied input (unlike institution_id/user_id which are always
    derived server-side from the session), so ownership is checked, not
    assumed — same pattern as practice.py's explicit skill_id validation."""
    rows = db.select("tutor_conversations", {
        "id": f"eq.{conversation_id}",
        "user_id": f"eq.{user.user_id}",
        "institution_id": f"eq.{user.institution_id}",
        "select": "id,course_id,skill_id,title,created_at,updated_at",
        "limit": "1",
    })
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "conversation not found")
    return rows[0]


def _conversation_view(row: dict) -> dict:
    return {
        "id": row["id"],
        "courseId": row["course_id"],
        "skillId": row.get("skill_id"),
        "title": row.get("title"),
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


class CreateConversation(BaseModel):
    course_id: str
    skill_id: str | None = None


@router.post("/conversations")
def create_conversation(body: CreateConversation, user: CurrentUser = Depends(get_current_user)):
    rows = db.insert("tutor_conversations", [{
        "institution_id": user.institution_id,
        "course_id": body.course_id,
        "user_id": user.user_id,
        "skill_id": body.skill_id,
    }])
    return _conversation_view(rows[0])


@router.get("/conversations")
def list_conversations(course_id: str, user: CurrentUser = Depends(get_current_user)):
    rows = db.select("tutor_conversations", {
        "institution_id": f"eq.{user.institution_id}",
        "user_id": f"eq.{user.user_id}",
        "course_id": f"eq.{course_id}",
        "select": "id,course_id,skill_id,title,created_at,updated_at",
        "order": "updated_at.desc",
    })
    return {"conversations": [_conversation_view(r) for r in rows]}


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str, user: CurrentUser = Depends(get_current_user)):
    convo = _owned_conversation(conversation_id, user)
    messages = db.select("tutor_messages", {
        "conversation_id": f"eq.{conversation_id}",
        "select": "id,role,content,style,created_at",
        "order": "created_at.asc",
    })
    return {
        **_conversation_view(convo),
        "messages": [{
            "id": m["id"], "role": m["role"], "content": m["content"],
            "style": m.get("style"), "createdAt": m["created_at"],
        } for m in messages],
    }


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, user: CurrentUser = Depends(get_current_user)):
    _owned_conversation(conversation_id, user)  # 404s if not owned, before deleting
    db.delete("tutor_conversations", {"id": f"eq.{conversation_id}"})
    return {"deleted": True}


class Ask(BaseModel):
    course_id: str
    question: str
    style: Literal["default", "eli5", "detail"] = "default"
    # Omitted entirely (the default): stateless, single-turn, exactly the
    # original behavior this endpoint always had — this is what Lessons'
    # Hint and Flashcards' Hint/Explain/Ask-a-friend already call via
    # useTutorAsk, and none of that should start persisting conversations
    # just because this migration exists. Only pass this when the caller
    # actually wants a real, resumable thread (the freeform tutor chat) —
    # create one first via POST /tutor/conversations, then pass its id on
    # every /ask in that thread.
    conversation_id: str | None = None


@router.post("/ask")
def ask(body: Ask, user: CurrentUser = Depends(get_current_user)):
    if not body.conversation_id:
        # Original stateless path, unchanged. No conversation touched, no
        # history, no persistence — a canned hint stays a canned hint.
        chunks = rag.retrieve(
            institution_id=user.institution_id, course_id=body.course_id, query=body.question,
        )
        context = "\n".join(c.get("chunk_text", "") for c in chunks)
        prompt = safe_context(user, f"Course context:\n{context}\n\nQuestion: {body.question}")
        system = _SYSTEM + _STYLE_HINTS.get(body.style, "")
        return {"answer": model_router.answer(system=system, user_text=prompt)}

    convo = _owned_conversation(body.conversation_id, user)

    prior = db.select("tutor_messages", {
        "conversation_id": f"eq.{convo['id']}",
        "select": "role,content",
        "order": "created_at.desc",
        "limit": str(_HISTORY_TURNS),
    })
    history = [
        {"role": m["role"], "content": [{"text": m["content"]}]}
        for m in reversed(prior)  # selected newest-first for the limit, replayed oldest-first
    ]

    chunks = rag.retrieve(
        institution_id=user.institution_id, course_id=convo["course_id"], query=body.question,
    )
    context = "\n".join(c.get("chunk_text", "") for c in chunks)
    prompt = safe_context(user, f"Course context:\n{context}\n\nQuestion: {body.question}")
    system = _SYSTEM + _STYLE_HINTS.get(body.style, "")
    answer_text = model_router.answer(system=system, user_text=prompt, history=history)

    db.insert("tutor_messages", [
        {"conversation_id": convo["id"], "role": "user", "content": body.question},
        {"conversation_id": convo["id"], "role": "assistant", "content": answer_text, "style": body.style},
    ])
    updates: dict = {"updated_at": "now()"}
    if not convo.get("title"):
        # First message in the thread: derive a short title from it rather
        # than leaving it null forever or spending a model call naming a
        # chat nobody's read yet. No attempt at cleverness here.
        updates["title"] = body.question[:60] + ("…" if len(body.question) > 60 else "")
    db.update("tutor_conversations", {"id": f"eq.{convo['id']}"}, updates)

    return {"answer": answer_text, "conversationId": convo["id"]}
