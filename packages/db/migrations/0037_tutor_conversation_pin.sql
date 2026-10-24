-- APPROVAL-05 / WI-21; TUTOR-REQ-003. Additive; owner read policies unchanged.
alter table public.tutor_conversations
  add column pinned_at timestamptz null;
