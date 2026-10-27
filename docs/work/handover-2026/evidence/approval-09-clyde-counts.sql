-- APPROVAL-09: prepared for Fred; NOT RUN by Codex.
-- Replace these four UUID placeholders privately. Do not send identifiers,
-- messages, chunks, names from other profiles, or any raw row to a chat.
-- The response UUID is the assistant message that first greeted this user
-- as Clyde. Using that boundary avoids counting the reported reply itself
-- as evidence that the name was already in the model's input history.
-- All text searches are limited to the owned conversation, its course
-- material, its own attachments, or this user's profile.
begin read only;
with params as (
  select
    '<institution-uuid>'::uuid as institution_id,
    '<Hanna-validated-user-uuid>'::uuid as user_id,
    '<owned-conversation-uuid>'::uuid as conversation_id,
    '<first-Clyde-assistant-message-uuid>'::uuid as response_id
), target as (
  select c.id, c.institution_id, c.user_id, c.course_id
  from public.tutor_conversations c
  join params p on c.id = p.conversation_id
    and c.institution_id = p.institution_id and c.user_id = p.user_id
), incident as (
  select m.id, m.created_at
  from public.tutor_messages m
  join target t on m.conversation_id = t.id
  join params p on m.id = p.response_id
  where m.role = 'assistant'
), prior_window as (
  select m.role, m.content
  from public.tutor_messages m
  join target t on m.conversation_id = t.id
  cross join incident i
  where m.created_at < i.created_at
  order by m.created_at desc
  limit 10
)
select
  (select count(*) from target) as owned_conversation_count,
  (select count(*) from incident) as incident_message_count,
  (select count(*) from public.content_items c join target t
     on c.institution_id=t.institution_id and c.course_id=t.course_id
     where c.chunk_text ilike '%Clyde%') as course_chunk_matches,
  (select count(*) from public.content_items c join target t
     on c.institution_id=t.institution_id and c.course_id=t.course_id
     where c.embedding is not null and c.chunk_text ilike '%Clyde%')
       as embedded_course_chunk_matches,
  (select count(*) from prior_window where content ilike '%Clyde%')
       as prior_history_window_matches,
  (select count(*) from prior_window
     where role='user' and content ilike '%Clyde%') as prior_user_message_matches,
  (select count(*) from prior_window
     where role='assistant' and content ilike '%Clyde%') as prior_assistant_message_matches,
  (select count(*) from public.tutor_messages m join target t
     on m.conversation_id=t.id cross join incident i
     where m.role='user' and m.created_at=i.created_at
       and m.content ilike '%Clyde%') as same_timestamp_user_question_matches,
  (select count(*) from public.tutor_attachments a join target t
     on a.conversation_id=t.id and a.institution_id=t.institution_id
       and a.user_id=t.user_id cross join incident i
     where a.status='ready' and a.created_at<i.created_at
       and (a.filename ilike '%Clyde%' or a.extracted_text ilike '%Clyde%'))
       as own_ready_attachment_matches,
  (select count(*) from public.tutor_attachments a join target t
     on a.conversation_id=t.id cross join incident i
     where a.created_at<i.created_at
       and (a.institution_id<>t.institution_id or a.user_id<>t.user_id))
       as attachment_ownership_mismatch_count,
  (select count(*) from public.user_profiles profile
     join public.users u on u.id=profile.user_id
     join target t on u.id=t.user_id and u.institution_id=t.institution_id
     where profile.display_name ilike '%Clyde%') as own_display_name_matches,
  (select count(*) from information_schema.tables
     where table_schema='public' and table_name ~ '(memory|summary)')
       as memory_or_summary_named_table_count;
rollback;

-- Required: owned_conversation_count=1 and incident_message_count=1.
-- Otherwise stop; zero matches cannot be interpreted as absence of the name.
-- Any attachment ownership mismatch is a stop/escalation, not permission
-- to read the other attachment's content. Its text is never searched here.
-- There is no persisted free-text personal memory/summary table in the
-- reviewed migrations or Tutor call path. A nonzero catalogue count is
-- schema drift to review, not a reason to invent queries for unknown tables.
-- The current question is not persisted until after generation. Same-time
-- user counts are only a diagnostic for the normal paired insert, not proof
-- of the original request payload. Equal timestamps, later edits/deletes,
-- later uploads and unretained retrieval results limit causal attribution.
