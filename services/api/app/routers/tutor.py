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

Stage 4: private study-aid uploads. A student can attach a file (.txt,
.md, .pdf, 5MB cap) to one of their own conversations — migration 0011,
tutor_attachments + a private Supabase Storage bucket. Explicitly NOT the
shared RAG ingest pipeline: this never touches content_items or the
course-wide chunk/embed index, it's scoped to exactly the one
conversation it was uploaded into. See the migration's own comment for
why (institution-approved-content review gate, copyright exposure on
re-serving someone else's upload).
"""
from __future__ import annotations

import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.ai import rag, router as model_router
from app.ai.deidentify import safe_context
from app.db import storage
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

# Matches the bucket's own file_size_limit/allowed_mime_types (migration
# 0011) — checked here too so an oversized or wrong-type file fails fast,
# before spending effort extracting text, not just left to Storage's own
# rejection after the fact.
_MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024
_ALLOWED_MIME_TYPES = {"text/plain", "text/markdown", "application/pdf"}

# Some OS/browser combos report a generic or empty content-type for plain
# text files instead of text/plain or text/markdown. Falling back to the
# extension only when the reported type is one of these generic/empty
# values — a real, wrong mime type (e.g. an actual image mislabeled) still
# gets rejected, this only rescues the "browser didn't bother" case.
_GENERIC_MIME_TYPES = {"", "application/octet-stream", "text/plain"}
_EXTENSION_MIME_FALLBACK = {".txt": "text/plain", ".md": "text/markdown", ".pdf": "application/pdf"}

# A cap on how much of an attachment's extracted text goes into any one
# prompt — the full text is always stored, this only bounds what gets
# assembled into context, so one long PDF can't blow out the model's
# context window on every single turn of the conversation it's attached to.
_MAX_ATTACHMENT_CONTEXT_CHARS = 8000
# A SEPARATE cap on the total across every attachment in the conversation
# combined. Per-file capping alone doesn't bound this — a conversation
# with many small files could still add up to an unbounded total even
# with each one individually capped.
_MAX_TOTAL_ATTACHMENT_CONTEXT_CHARS = 16000


def _extract_text(content: bytes, mime_type: str) -> str:
    """Best-effort text extraction for the two supported non-plain-text
    shapes uploads can arrive in. Anything that fails to parse raises —
    the caller marks the attachment 'failed' rather than crashing the
    request, the file is kept either way, it just contributes no context."""
    if mime_type == "application/pdf":
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return content.decode("utf-8", errors="replace")


def _safe_filename(name: str | None) -> str:
    """Collapse a client-supplied filename to just its basename before it
    becomes part of a storage path. Path(...).name strips any directory
    components — a crafted "../../other-user-id/other-conv-id/x" collapses
    to just "x" rather than escaping this user's folder. This runs on the
    service-role write path (storage.upload/db.insert both bypass RLS), so
    the filename was fully trusted before this fix; a path that landed in
    another user's folder would then be exposed by THEIR OWN self-scoped
    read policy, which has no way to know the object doesn't belong there."""
    base = Path(name or "upload").name
    base = "".join(c for c in base if c.isprintable()) or "upload"
    return base[:200]


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
    if body.skill_id:
        # Client-supplied, not yet sent by any UI (a future "ask about
        # this lesson step" flow would be the first caller) — validated
        # the same way practice.py checks an explicit skill_id, rather
        # than trusting the foreign key alone to catch a skill from a
        # different course.
        exists = db.select("skills", {
            "id": f"eq.{body.skill_id}", "course_id": f"eq.{body.course_id}",
            "institution_id": f"eq.{user.institution_id}",
            "select": "id", "limit": "1",
        })
        if not exists:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "skill not found")
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
    attachments = db.select("tutor_attachments", {
        "conversation_id": f"eq.{conversation_id}",
        "select": "id,filename,mime_type,size_bytes,status,created_at",
        "order": "created_at.asc",
    })
    return {
        **_conversation_view(convo),
        "messages": [{
            "id": m["id"], "role": m["role"], "content": m["content"],
            "style": m.get("style"), "createdAt": m["created_at"],
        } for m in messages],
        "attachments": [_attachment_view(a) for a in attachments],
    }


def _attachment_view(row: dict) -> dict:
    return {
        "id": row["id"],
        "filename": row["filename"],
        "mimeType": row["mime_type"],
        "sizeBytes": row["size_bytes"],
        "status": row["status"],
        "createdAt": row["created_at"],
    }


@router.post("/conversations/{conversation_id}/attachments")
def upload_attachment(
    conversation_id: str,
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
):
    convo = _owned_conversation(conversation_id, user)
    filename = _safe_filename(file.filename)

    mime_type = file.content_type or ""
    if mime_type in _GENERIC_MIME_TYPES:
        ext = Path(filename).suffix.lower()
        mime_type = _EXTENSION_MIME_FALLBACK.get(ext, mime_type or "application/octet-stream")
    if mime_type not in _ALLOWED_MIME_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"unsupported file type: {mime_type}. Allowed: .txt, .md, .pdf",
        )
    content = file.file.read()
    if len(content) > _MAX_ATTACHMENT_BYTES:
        raise HTTPException(413, "file exceeds 5MB limit")

    row = db.insert("tutor_attachments", [{
        "institution_id": user.institution_id,
        "user_id": user.user_id,
        "conversation_id": convo["id"],
        # Placeholder path filled in below once we have the row's real id —
        # the {id}-{filename} convention needs the id first, and id is
        # generated by the insert itself.
        "storage_path": "",
        "filename": filename,
        "mime_type": mime_type,
        "size_bytes": len(content),
        "status": "processing",
    }])[0]

    path = f"{user.user_id}/{convo['id']}/{row['id']}-{row['filename']}"
    db.update("tutor_attachments", {"id": f"eq.{row['id']}"}, {"storage_path": path})

    try:
        storage.upload(path, content, mime_type)
        text = _extract_text(content, mime_type)
        db.update("tutor_attachments", {"id": f"eq.{row['id']}"}, {
            "status": "ready", "extracted_text": text,
        })
        row["status"] = "ready"
    except Exception:
        # Extraction or upload failed — the metadata row stays (so the
        # student sees the file listed and knows something went wrong),
        # just contributes no context to the conversation. Never let a
        # bad PDF 500 the whole request.
        db.update("tutor_attachments", {"id": f"eq.{row['id']}"}, {"status": "failed"})
        row["status"] = "failed"

    return _attachment_view(row)


@router.delete("/conversations/{conversation_id}/attachments/{attachment_id}")
def delete_attachment(
    conversation_id: str, attachment_id: str, user: CurrentUser = Depends(get_current_user),
):
    _owned_conversation(conversation_id, user)
    rows = db.select("tutor_attachments", {
        "id": f"eq.{attachment_id}", "conversation_id": f"eq.{conversation_id}",
        "select": "storage_path", "limit": "1",
    })
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "attachment not found")
    storage.delete(rows[0]["storage_path"])
    db.delete("tutor_attachments", {"id": f"eq.{attachment_id}"})
    return {"deleted": True}


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, user: CurrentUser = Depends(get_current_user)):
    _owned_conversation(conversation_id, user)  # 404s if not owned, before deleting
    # Attachment rows cascade away with the conversation (FK on delete
    # cascade), but the actual bytes in Storage don't — they're a separate
    # system with no knowledge of the Postgres cascade, and would sit
    # orphaned under this user's folder forever otherwise. Delete the
    # objects first, same as the per-attachment endpoint does one at a time.
    attachments = db.select("tutor_attachments", {
        "conversation_id": f"eq.{conversation_id}", "select": "storage_path",
    })
    for a in attachments:
        storage.delete(a["storage_path"])
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

    attachments = db.select("tutor_attachments", {
        "conversation_id": f"eq.{convo['id']}", "status": "eq.ready",
        "select": "filename,extracted_text",
    })
    attachment_block = ""
    if attachments:
        # Labeled distinctly from course context — this is the student's
        # own uploaded material, not institution-approved course content,
        # and the model shouldn't treat the two the same way (course
        # content is retrieval-grounded and vetted; this is whatever the
        # student happened to attach).
        parts = [
            f"--- {a['filename']} ---\n{(a.get('extracted_text') or '')[:_MAX_ATTACHMENT_CONTEXT_CHARS]}"
            for a in attachments
        ]
        joined = "\n\n".join(parts)[:_MAX_TOTAL_ATTACHMENT_CONTEXT_CHARS]
        attachment_block = "\n\nMaterial the student uploaded (their own notes, not course content):\n" + joined

    prompt = safe_context(
        user, f"Course context:\n{context}{attachment_block}\n\nQuestion: {body.question}"
    )
    system = _SYSTEM + _STYLE_HINTS.get(body.style, "")
    answer_text = model_router.answer(system=system, user_text=prompt, history=history)

    db.insert("tutor_messages", [
        {"conversation_id": convo["id"], "role": "user", "content": body.question},
        {"conversation_id": convo["id"], "role": "assistant", "content": answer_text, "style": body.style},
    ])
    updates: dict = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if not convo.get("title"):
        # First message in the thread: derive a short title from it rather
        # than leaving it null forever or spending a model call naming a
        # chat nobody's read yet. No attempt at cleverness here.
        updates["title"] = body.question[:60] + ("…" if len(body.question) > 60 else "")
    db.update("tutor_conversations", {"id": f"eq.{convo['id']}"}, updates)

    return {"answer": answer_text, "conversationId": convo["id"]}
