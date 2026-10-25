-- WI-25 / TWIN-REQ-010 / INSTR-REQ-010: stable evidence history keysets.
-- Index only. Hosted execution is maintainer-only under FG-6.
create index if not exists evidence_events_history_idx
on public.evidence_events (user_id, course_id, created_at desc, id desc);
