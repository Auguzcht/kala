-- =====================================================================
-- Kala — 0015_lms_identity_aliases.sql
-- A durable map from EVERY LMS identifier Kala has ever seen for a person
-- to the single Kala user it resolves to.
--
-- WHY THIS EXISTS. `users.lms_user_id` is written from two DIFFERENT
-- Blackboard identifiers depending on which code path runs:
--
--   LTI launch  -> payload["sub"]        e.g. "2aca8e5459054620993530550b5f0a93"
--   roster sync -> the connector's userId e.g. "_10_1"
--
-- `upsert_user` conflicts on (institution_id, lms_user_id), so when a student
-- is BOTH rostered and launched, the two paths create TWO user rows. The
-- roster-created row gets the enrollment (so the instructor sees them); the
-- launch-created row gets all the evidence (so their real work is invisible).
-- Confirmed live: 4 such pairs existed, one with 149 evidence rows stranded on
-- the invisible half.
--
-- The fix resolves a launch to an existing user by EMAIL before falling back
-- to a new row, and this table records the identifier pair so the resolution
-- does not depend on email staying present or unchanged forever. Email is a
-- good DISCOVERY signal (both paths already fetch it, and it matched exactly
-- in every observed duplicate pair) but a poor permanent key: it is mutable,
-- and Blackboard does not guarantee it is present on a launch at all.
--
-- After a launch has been seen once, `lms_user_id -> user_id` here is a
-- stable, exact lookup with no dependence on vendor guarantees about how
-- `sub` and `userId` relate. That relationship is exactly what is NOT
-- documented, which is why this table is populated by OBSERVATION rather
-- than computed.
--
-- One row per (institution, lms_user_id): an identifier belongs to exactly
-- one person. `user_id` cascades on delete so removing a user clears their
-- aliases.
-- =====================================================================

create table public.lms_identity_aliases (
  institution_id uuid not null references public.institutions(id) on delete cascade,
  -- Any LMS identifier form: LTI `sub`, REST userId, whatever a future
  -- connector hands us. Text, not uuid, because these are opaque strings.
  lms_user_id    text not null,
  user_id        uuid not null references public.users(id) on delete cascade,
  -- How this alias was first learned. Diagnostic only, never load-bearing:
  -- 'launch' (LTI sub), 'roster' (connector userId), 'email_match' (resolved
  -- to an existing user by email), 'backfill' (written by the repair script).
  source         text not null default 'unknown',
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  primary key (institution_id, lms_user_id)
);
create index lms_identity_aliases_user_idx
  on public.lms_identity_aliases (user_id);

alter table public.lms_identity_aliases enable row level security;

-- Students may read their OWN aliases (harmless, and useful if a future
-- surface ever needs to show which LMS ids map to the signed-in user).
-- Staff may read their institution's. Mirrors the evidence_events shape.
-- Writes are service-role only (the API), same as users/user_profiles.
create policy lms_identity_aliases_read on public.lms_identity_aliases
  for select to authenticated
  using (
    user_id = auth.uid()
    or (public.is_staff() and institution_id = public.current_institution())
  );
grant select on public.lms_identity_aliases to authenticated;

-- Backfill what we already know: every existing user's current lms_user_id is
-- by definition an alias for them. This makes the table immediately useful
-- for the reconciliations below, rather than empty until the next launch.
insert into public.lms_identity_aliases (institution_id, lms_user_id, user_id, source)
select institution_id, lms_user_id, id, 'backfill'
from public.users
on conflict (institution_id, lms_user_id) do nothing;

-- Backfill email aliases too, but ONLY where the email is unambiguous — a
-- duplicate email would map one identifier to two people, which is exactly
-- the ambiguity this table exists to remove. `kala.student1@example.com`
-- appears twice today, so it is deliberately skipped here; the repair script
-- resolves those by choosing the account that actually carries the work.
insert into public.lms_identity_aliases (institution_id, lms_user_id, user_id, source)
select u.institution_id, 'email:' || lower(p.email), u.id, 'backfill'
from public.users u
join public.user_profiles p on p.user_id = u.id
where p.email is not null and p.email <> ''
  and lower(p.email) in (
    select lower(up.email)
    from public.user_profiles up
    where up.email is not null and up.email <> ''
    group by lower(up.email)
    having count(*) = 1
  )
on conflict (institution_id, lms_user_id) do nothing;
