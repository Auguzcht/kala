-- WI-26 / INSTR-REQ-009: tighten direct recommendation visibility and writes.
-- Applied predecessors and authorization helper definitions remain unchanged.
begin;

alter policy recs_read on public.recommendations using (
  institution_id = public.current_institution()
  and exists (
    select 1 from public.courses c
    where c.id = recommendations.course_id
      and c.institution_id = recommendations.institution_id
  )
  and (
    (public.current_app_role() = 'student'
      and user_id = auth.uid()
      and status in ('approved', 'modified', 'completed'))
    or (exists (
    select 1 from public.enrollments learner
    join public.users learner_user on learner_user.id = learner.user_id
      and learner_user.institution_id = learner.institution_id
      and learner_user.role = 'student'
    where learner.user_id = recommendations.user_id
      and learner.course_id = recommendations.course_id
      and learner.institution_id = recommendations.institution_id
      and learner.role = 'student'
  ) and public.current_app_role() = 'instructor'
      and public.teaches(course_id)
      and exists (
        select 1 from public.enrollments e
        where e.course_id = recommendations.course_id
          and e.institution_id = recommendations.institution_id
          and e.user_id = auth.uid() and e.role = 'instructor'
      ))
    or (public.is_admin() and exists (
    select 1 from public.enrollments learner
    join public.users learner_user on learner_user.id = learner.user_id
      and learner_user.institution_id = learner.institution_id
      and learner_user.role = 'student'
    where learner.user_id = recommendations.user_id
      and learner.course_id = recommendations.course_id
      and learner.institution_id = recommendations.institution_id
      and learner.role = 'student'
  ))
  )
);

alter policy recs_insert on public.recommendations with check (
  institution_id = public.current_institution()
  and exists (
    select 1 from public.enrollments learner
    join public.users learner_user on learner_user.id = learner.user_id
      and learner_user.institution_id = learner.institution_id
      and learner_user.role = 'student'
    where learner.user_id = recommendations.user_id
      and learner.course_id = recommendations.course_id
      and learner.institution_id = recommendations.institution_id
      and learner.role = 'student'
  )
  and exists (
    select 1 from public.courses c
    where c.id = recommendations.course_id
      and c.institution_id = recommendations.institution_id
  )
  and (
    (public.current_app_role() = 'instructor'
      and public.teaches(course_id)
      and exists (
        select 1 from public.enrollments e
        where e.course_id = recommendations.course_id
          and e.institution_id = recommendations.institution_id
          and e.user_id = auth.uid() and e.role = 'instructor'
      ))
    or public.is_admin()
  )
);

alter policy recs_update on public.recommendations using (
  institution_id = public.current_institution()
  and exists (
    select 1 from public.enrollments learner
    join public.users learner_user on learner_user.id = learner.user_id
      and learner_user.institution_id = learner.institution_id
      and learner_user.role = 'student'
    where learner.user_id = recommendations.user_id
      and learner.course_id = recommendations.course_id
      and learner.institution_id = recommendations.institution_id
      and learner.role = 'student'
  )
  and exists (
    select 1 from public.courses c
    where c.id = recommendations.course_id
      and c.institution_id = recommendations.institution_id
  )
  and (
    (public.current_app_role() = 'instructor'
      and public.teaches(course_id)
      and exists (
        select 1 from public.enrollments e
        where e.course_id = recommendations.course_id
          and e.institution_id = recommendations.institution_id
          and e.user_id = auth.uid() and e.role = 'instructor'
      ))
    or public.is_admin()
  )
) with check (
  institution_id = public.current_institution()
  and exists (
    select 1 from public.enrollments learner
    join public.users learner_user on learner_user.id = learner.user_id
      and learner_user.institution_id = learner.institution_id
      and learner_user.role = 'student'
    where learner.user_id = recommendations.user_id
      and learner.course_id = recommendations.course_id
      and learner.institution_id = recommendations.institution_id
      and learner.role = 'student'
  )
  and exists (
    select 1 from public.courses c
    where c.id = recommendations.course_id
      and c.institution_id = recommendations.institution_id
  )
  and (
    (public.current_app_role() = 'instructor'
      and public.teaches(course_id)
      and exists (
        select 1 from public.enrollments e
        where e.course_id = recommendations.course_id
          and e.institution_id = recommendations.institution_id
          and e.user_id = auth.uid() and e.role = 'instructor'
      ))
    or public.is_admin()
  )
);

-- Personal learning rows: preserve non-staff self access; staff must teach
-- this course in the token institution, or administer that institution.
-- Do not query enrollments or courses here: course/identity policies consult
-- this table. The existing definer helper avoids recursive policy expansion.
alter policy enroll_read on public.enrollments using (
  institution_id = public.current_institution()
  and (
    (user_id = auth.uid() and not public.is_staff())
    or (public.current_app_role() = 'instructor' and public.teaches(course_id)
        and (role = 'student' or (user_id = auth.uid() and role = 'instructor')))
    or public.is_admin()
  )
);

alter policy evidence_read on public.evidence_events using (
  institution_id = public.current_institution()
  and (
    (user_id = auth.uid() and not public.is_staff())
    or (exists (
    select 1 from public.enrollments learner
    join public.users learner_user on learner_user.id = learner.user_id
      and learner_user.institution_id = learner.institution_id
      and learner_user.role = 'student'
    where learner.user_id = evidence_events.user_id
      and learner.course_id = evidence_events.course_id
      and learner.institution_id = evidence_events.institution_id
      and learner.role = 'student'
  ) and institution_id = public.current_institution()
  and exists (select 1 from public.courses c where c.id = evidence_events.course_id
              and c.institution_id = evidence_events.institution_id)
  and (public.is_admin() or (
    public.current_app_role() = 'instructor' and public.teaches(course_id)
    and exists (select 1 from public.enrollments e
                where e.course_id = evidence_events.course_id
                  and e.institution_id = evidence_events.institution_id
                  and e.user_id = auth.uid() and e.role = 'instructor')
  )))
  )
);

alter policy mastery_read on public.mastery_state using (
  institution_id = public.current_institution()
  and (
    (user_id = auth.uid() and not public.is_staff())
    or (exists (
    select 1 from public.enrollments learner
    join public.users learner_user on learner_user.id = learner.user_id
      and learner_user.institution_id = learner.institution_id
      and learner_user.role = 'student'
    where learner.user_id = mastery_state.user_id
      and learner.course_id = mastery_state.course_id
      and learner.institution_id = mastery_state.institution_id
      and learner.role = 'student'
  ) and institution_id = public.current_institution()
  and exists (select 1 from public.courses c where c.id = mastery_state.course_id
              and c.institution_id = mastery_state.institution_id)
  and (public.is_admin() or (
    public.current_app_role() = 'instructor' and public.teaches(course_id)
    and exists (select 1 from public.enrollments e
                where e.course_id = mastery_state.course_id
                  and e.institution_id = mastery_state.institution_id
                  and e.user_id = auth.uid() and e.role = 'instructor')
  )))
  )
);

alter policy readiness_read on public.readiness_snapshots using (
  institution_id = public.current_institution()
  and (
    (user_id = auth.uid() and not public.is_staff())
    or (exists (
    select 1 from public.enrollments learner
    join public.users learner_user on learner_user.id = learner.user_id
      and learner_user.institution_id = learner.institution_id
      and learner_user.role = 'student'
    where learner.user_id = readiness_snapshots.user_id
      and learner.course_id = readiness_snapshots.course_id
      and learner.institution_id = readiness_snapshots.institution_id
      and learner.role = 'student'
  ) and institution_id = public.current_institution()
  and exists (select 1 from public.courses c where c.id = readiness_snapshots.course_id
              and c.institution_id = readiness_snapshots.institution_id)
  and (public.is_admin() or (
    public.current_app_role() = 'instructor' and public.teaches(course_id)
    and exists (select 1 from public.enrollments e
                where e.course_id = readiness_snapshots.course_id
                  and e.institution_id = readiness_snapshots.institution_id
                  and e.user_id = auth.uid() and e.role = 'instructor')
  )))
  )
);

alter policy srs_read on public.srs_state using (
  institution_id = public.current_institution()
  and (
    (user_id = auth.uid() and not public.is_staff())
    or (exists (
    select 1 from public.enrollments learner
    join public.users learner_user on learner_user.id = learner.user_id
      and learner_user.institution_id = learner.institution_id
      and learner_user.role = 'student'
    where learner.user_id = srs_state.user_id
      and learner.course_id = srs_state.course_id
      and learner.institution_id = srs_state.institution_id
      and learner.role = 'student'
  ) and institution_id = public.current_institution()
  and exists (select 1 from public.courses c where c.id = srs_state.course_id
              and c.institution_id = srs_state.institution_id)
  and (public.is_admin() or (
    public.current_app_role() = 'instructor' and public.teaches(course_id)
    and exists (select 1 from public.enrollments e
                where e.course_id = srs_state.course_id
                  and e.institution_id = srs_state.institution_id
                  and e.user_id = auth.uid() and e.role = 'instructor')
  )))
  )
);

alter policy quiz_set_attempts_read on public.quiz_set_attempts using (
  institution_id = public.current_institution()
  and (
    (user_id = auth.uid() and not public.is_staff())
    or (exists (
    select 1 from public.enrollments learner
    join public.users learner_user on learner_user.id = learner.user_id
      and learner_user.institution_id = learner.institution_id
      and learner_user.role = 'student'
    where learner.user_id = quiz_set_attempts.user_id
      and learner.course_id = quiz_set_attempts.course_id
      and learner.institution_id = quiz_set_attempts.institution_id
      and learner.role = 'student'
  ) and institution_id = public.current_institution()
  and exists (select 1 from public.courses c where c.id = quiz_set_attempts.course_id
              and c.institution_id = quiz_set_attempts.institution_id)
  and (public.is_admin() or (
    public.current_app_role() = 'instructor' and public.teaches(course_id)
    and exists (select 1 from public.enrollments e
                where e.course_id = quiz_set_attempts.course_id
                  and e.institution_id = quiz_set_attempts.institution_id
                  and e.user_id = auth.uid() and e.role = 'instructor')
  )))
  )
);

alter policy item_exposures_read on public.item_exposures using (
  institution_id = public.current_institution()
  and (
    (user_id = auth.uid() and not public.is_staff())
    or (exists (
    select 1 from public.enrollments learner
    join public.users learner_user on learner_user.id = learner.user_id
      and learner_user.institution_id = learner.institution_id
      and learner_user.role = 'student'
    where learner.user_id = item_exposures.user_id
      and learner.course_id = item_exposures.course_id
      and learner.institution_id = item_exposures.institution_id
      and learner.role = 'student'
  ) and institution_id = public.current_institution()
  and exists (select 1 from public.courses c where c.id = item_exposures.course_id
              and c.institution_id = item_exposures.institution_id)
  and (public.is_admin() or (
    public.current_app_role() = 'instructor' and public.teaches(course_id)
    and exists (select 1 from public.enrollments e
                where e.course_id = item_exposures.course_id
                  and e.institution_id = item_exposures.institution_id
                  and e.user_id = auth.uid() and e.role = 'instructor')
  )))
  )
);

alter policy item_reviews_read on public.item_reviews using (
  institution_id = public.current_institution()
  and (
    (user_id = auth.uid() and not public.is_staff())
    or (exists (
    select 1 from public.enrollments learner
    join public.users learner_user on learner_user.id = learner.user_id
      and learner_user.institution_id = learner.institution_id
      and learner_user.role = 'student'
    where learner.user_id = item_reviews.user_id
      and learner.course_id = item_reviews.course_id
      and learner.institution_id = item_reviews.institution_id
      and learner.role = 'student'
  ) and institution_id = public.current_institution()
  and exists (select 1 from public.courses c where c.id = item_reviews.course_id
              and c.institution_id = item_reviews.institution_id)
  and (public.is_admin() or (
    public.current_app_role() = 'instructor' and public.teaches(course_id)
    and exists (select 1 from public.enrollments e
                where e.course_id = item_reviews.course_id
                  and e.institution_id = item_reviews.institution_id
                  and e.user_id = auth.uid() and e.role = 'instructor')
  )))
  )
);

-- Identity reads retain self/admin access. Instructors see only identities
-- sharing a course they currently teach; the enrollment policy is nonrecursive.
alter policy users_read on public.users using (
  id = auth.uid()
  or (institution_id = public.current_institution() and (
    (public.is_admin() and role <> 'student')
    or (role = 'student' and exists (
      select 1 from public.enrollments learner
      join public.courses c on c.id = learner.course_id
        and c.institution_id = learner.institution_id
      where learner.user_id = users.id and learner.role = 'student'
        and learner.institution_id = users.institution_id
        and (public.is_admin() or (
          public.current_app_role() = 'instructor' and public.teaches(learner.course_id)
          and exists (select 1 from public.enrollments teacher
                      where teacher.course_id = learner.course_id
                        and teacher.institution_id = learner.institution_id
                        and teacher.user_id = auth.uid() and teacher.role = 'instructor')
        ))
    ))
  ))
);

alter policy lms_identity_aliases_read on public.lms_identity_aliases using (
  user_id = auth.uid()
  or (institution_id = public.current_institution() and (
    (public.is_admin() and exists (
      select 1 from public.users u where u.id = lms_identity_aliases.user_id
        and u.institution_id = lms_identity_aliases.institution_id and u.role <> 'student'
    ))
    or exists (
      select 1 from public.enrollments learner
      join public.users u on u.id = learner.user_id
        and u.institution_id = learner.institution_id and u.role = 'student'
      join public.courses c on c.id = learner.course_id
        and c.institution_id = learner.institution_id
      where learner.user_id = lms_identity_aliases.user_id and learner.role = 'student'
        and learner.institution_id = lms_identity_aliases.institution_id
        and (public.is_admin() or (
          public.current_app_role() = 'instructor' and public.teaches(learner.course_id)
          and exists (select 1 from public.enrollments teacher
                      where teacher.course_id = learner.course_id
                        and teacher.institution_id = learner.institution_id
                        and teacher.user_id = auth.uid() and teacher.role = 'instructor')
        ))
    )
  ))
);

-- Shared course/curriculum rows retain their original non-staff audience.
-- Only staff admission is narrowed; granted researcher reads remain intact.
alter policy courses_read on public.courses using (
  (institution_id = public.current_institution() or public.has_grant(institution_id))
  and (not public.is_staff() or (institution_id = public.current_institution()
    and (public.is_admin() or (
      public.current_app_role() = 'instructor' and public.teaches(id)
      and exists (select 1 from public.enrollments teacher
                  where teacher.course_id = courses.id
                    and teacher.institution_id = courses.institution_id
                    and teacher.user_id = auth.uid() and teacher.role = 'instructor')
    ))))
);

alter policy skills_read on public.skills using (
  (institution_id = public.current_institution())
  and (not public.is_staff() or (institution_id = public.current_institution()
  and exists (select 1 from public.courses c where c.id = skills.course_id
              and c.institution_id = skills.institution_id)
  and (public.is_admin() or (
    public.current_app_role() = 'instructor' and public.teaches(course_id)
    and exists (select 1 from public.enrollments e
                where e.course_id = skills.course_id
                  and e.institution_id = skills.institution_id
                  and e.user_id = auth.uid() and e.role = 'instructor')
  ))))
);

alter policy assess_read on public.assessments using (
  (institution_id = public.current_institution())
  and (not public.is_staff() or (institution_id = public.current_institution()
  and exists (select 1 from public.courses c where c.id = assessments.course_id
              and c.institution_id = assessments.institution_id)
  and (public.is_admin() or (
    public.current_app_role() = 'instructor' and public.teaches(course_id)
    and exists (select 1 from public.enrollments e
                where e.course_id = assessments.course_id
                  and e.institution_id = assessments.institution_id
                  and e.user_id = auth.uid() and e.role = 'instructor')
  ))))
);

alter policy lessons_read on public.guided_lessons using (
  (institution_id = public.current_institution())
  and (not public.is_staff() or (institution_id = public.current_institution()
  and exists (select 1 from public.courses c where c.id = guided_lessons.course_id
              and c.institution_id = guided_lessons.institution_id)
  and (public.is_admin() or (
    public.current_app_role() = 'instructor' and public.teaches(course_id)
    and exists (select 1 from public.enrollments e
                where e.course_id = guided_lessons.course_id
                  and e.institution_id = guided_lessons.institution_id
                  and e.user_id = auth.uid() and e.role = 'instructor')
  ))))
);

-- Staff-only content/operational reads: reject stale-role/foreign claims.
alter policy content_read on public.content_items using (
  institution_id = public.current_institution()
  and exists (select 1 from public.courses c where c.id = content_items.course_id
              and c.institution_id = content_items.institution_id)
  and (public.is_admin() or (
    public.current_app_role() = 'instructor' and public.teaches(course_id)
    and exists (select 1 from public.enrollments e
                where e.course_id = content_items.course_id
                  and e.institution_id = content_items.institution_id
                  and e.user_id = auth.uid() and e.role = 'instructor')
  ))
);

alter policy items_read on public.generated_items using (
  institution_id = public.current_institution()
  and exists (select 1 from public.courses c where c.id = generated_items.course_id
              and c.institution_id = generated_items.institution_id)
  and (public.is_admin() or (
    public.current_app_role() = 'instructor' and public.teaches(course_id)
    and exists (select 1 from public.enrollments e
                where e.course_id = generated_items.course_id
                  and e.institution_id = generated_items.institution_id
                  and e.user_id = auth.uid() and e.role = 'instructor')
  ))
);

alter policy quiz_sets_read on public.quiz_sets using (
  institution_id = public.current_institution()
  and exists (select 1 from public.courses c where c.id = quiz_sets.course_id
              and c.institution_id = quiz_sets.institution_id)
  and (public.is_admin() or (
    public.current_app_role() = 'instructor' and public.teaches(course_id)
    and exists (select 1 from public.enrollments e
                where e.course_id = quiz_sets.course_id
                  and e.institution_id = quiz_sets.institution_id
                  and e.user_id = auth.uid() and e.role = 'instructor')
  ))
);

alter policy ingest_jobs_read on public.ingest_jobs using (
  institution_id = public.current_institution()
  and exists (select 1 from public.courses c where c.id = ingest_jobs.course_id
              and c.institution_id = ingest_jobs.institution_id)
  and (public.is_admin() or (
    public.current_app_role() = 'instructor' and public.teaches(course_id)
    and exists (select 1 from public.enrollments e
                where e.course_id = ingest_jobs.course_id
                  and e.institution_id = ingest_jobs.institution_id
                  and e.user_id = auth.uid() and e.role = 'instructor')
  ))
);

-- Peer profile access remains admin-only; the users policy establishes an
-- enrolled learner (or institutional staff identity) without new helpers.
alter policy profiles_read on public.user_profiles using (
  user_id = auth.uid()
  or (public.is_admin() and public.user_institution(user_id) = public.current_institution()
    and exists (select 1 from public.users u where u.id = user_profiles.user_id
                and u.institution_id = public.current_institution()))
);

commit;
