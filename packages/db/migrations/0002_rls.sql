-- =====================================================================
-- Kala — 0002_rls.sql
-- Row Level Security. Default deny; explicit allows per role.
-- Roles come from the JWT `app_role` claim: student | instructor | admin |
-- researcher. The backend uses the service_role key for writes and bypasses
-- RLS; these policies govern the authenticated client path (defense in depth).
-- anon has no access to anything.
-- =====================================================================

-- Small security-definer helper to resolve a user's institution without
-- triggering users-table RLS inside a policy.
create or replace function public.user_institution(u uuid)
returns uuid language sql stable security definer
set search_path = ''
as $$ select institution_id from public.users where id = u $$;

-- Enable RLS on every table.
alter table public.institutions          enable row level security;
alter table public.users                 enable row level security;
alter table public.user_profiles         enable row level security;
alter table public.lti_launches          enable row level security;
alter table public.courses               enable row level security;
alter table public.enrollments           enable row level security;
alter table public.skills                enable row level security;
alter table public.content_items         enable row level security;
alter table public.assessments           enable row level security;
alter table public.evidence_events       enable row level security;
alter table public.mastery_state         enable row level security;
alter table public.readiness_snapshots   enable row level security;
alter table public.recommendations       enable row level security;
alter table public.consents              enable row level security;
alter table public.researchers           enable row level security;
alter table public.researcher_grants     enable row level security;
alter table public.data_subject_requests enable row level security;
alter table public.audit_log             enable row level security;

-- ---- institutions ----
create policy inst_read on public.institutions for select to authenticated
  using (id = public.current_institution() or public.has_grant(id));

-- ---- users ----
create policy users_read on public.users for select to authenticated
  using (
    id = auth.uid()
    or (public.is_staff() and institution_id = public.current_institution())
  );

-- ---- user_profiles (PII) ----
create policy profiles_read on public.user_profiles for select to authenticated
  using (
    user_id = auth.uid()
    or (public.is_admin() and public.user_institution(user_id) = public.current_institution())
  );

-- ---- lti_launches (security log, admin-only read) ----
create policy launches_read on public.lti_launches for select to authenticated
  using (public.is_admin() and institution_id = public.current_institution());

-- ---- courses ----
create policy courses_read on public.courses for select to authenticated
  using (institution_id = public.current_institution() or public.has_grant(institution_id));

-- ---- enrollments ----
create policy enroll_read on public.enrollments for select to authenticated
  using (
    user_id = auth.uid()
    or public.teaches(course_id)
    or (public.is_admin() and institution_id = public.current_institution())
  );

-- ---- skills / assessments (institution members read) ----
create policy skills_read on public.skills for select to authenticated
  using (institution_id = public.current_institution());
create policy assess_read on public.assessments for select to authenticated
  using (institution_id = public.current_institution());

-- ---- content_items (staff only; students never read raw chunks client-side) ----
create policy content_read on public.content_items for select to authenticated
  using (public.is_staff() and institution_id = public.current_institution());

-- ---- evidence_events (self / course staff / admin) ----
create policy evidence_read on public.evidence_events for select to authenticated
  using (
    user_id = auth.uid()
    or public.teaches(course_id)
    or (public.is_admin() and institution_id = public.current_institution())
  );

-- ---- mastery_state ----
create policy mastery_read on public.mastery_state for select to authenticated
  using (
    user_id = auth.uid()
    or public.teaches(course_id)
    or (public.is_admin() and institution_id = public.current_institution())
  );

-- ---- readiness_snapshots ----
create policy readiness_read on public.readiness_snapshots for select to authenticated
  using (
    user_id = auth.uid()
    or public.teaches(course_id)
    or (public.is_admin() and institution_id = public.current_institution())
  );

-- ---- recommendations ----
create policy recs_read on public.recommendations for select to authenticated
  using (
    user_id = auth.uid()
    or public.teaches(course_id)
    or (public.is_admin() and institution_id = public.current_institution())
  );

-- ---- consents (self read + self record; admin read within institution) ----
create policy consents_read on public.consents for select to authenticated
  using (
    user_id = auth.uid()
    or (public.is_admin() and institution_id = public.current_institution())
  );
create policy consents_insert on public.consents for insert to authenticated
  with check (user_id = auth.uid() and institution_id = public.current_institution());

-- ---- researchers (self only) ----
create policy researchers_read on public.researchers for select to authenticated
  using (id = auth.uid());

-- ---- researcher_grants (researcher sees own; institution admin sees theirs) ----
create policy grants_read on public.researcher_grants for select to authenticated
  using (
    researcher_id = auth.uid()
    or (public.is_admin() and institution_id = public.current_institution())
  );

-- ---- data_subject_requests (self file + read; admin read within institution) ----
create policy dsr_read on public.data_subject_requests for select to authenticated
  using (
    user_id = auth.uid()
    or (public.is_admin() and institution_id = public.current_institution())
  );
create policy dsr_insert on public.data_subject_requests for insert to authenticated
  with check (user_id = auth.uid() and institution_id = public.current_institution());

-- ---- audit_log (admin read only; inserts via security-definer trigger) ----
create policy audit_read on public.audit_log for select to authenticated
  using (public.is_admin() and institution_id = public.current_institution());

-- ---------------------------------------------------------------------
-- Grants (least privilege). anon gets nothing. authenticated gets SELECT on
-- readable tables and INSERT only where self-service; writes otherwise go
-- through the backend service_role (which bypasses RLS).
-- ---------------------------------------------------------------------

revoke all on all tables in schema public from anon;

grant usage on schema public to authenticated;

grant select on
  public.institutions, public.users, public.user_profiles, public.lti_launches,
  public.courses, public.enrollments, public.skills, public.assessments,
  public.content_items, public.evidence_events, public.mastery_state,
  public.readiness_snapshots, public.recommendations, public.consents,
  public.researchers, public.researcher_grants, public.data_subject_requests,
  public.audit_log
to authenticated;

grant insert on public.consents, public.data_subject_requests to authenticated;
