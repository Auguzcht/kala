-- These tests prove stop conditions, not a supported repair algorithm.
-- Every fixture identifier is generated here. No source payload is printed.
begin;
do $$
declare
 inst uuid; course uuid; canonical uuid; legacy uuid; item uuid;
 event_id uuid; shared_session uuid := gen_random_uuid();
 rows_before bigint; blocked boolean := false;
begin
 insert into public.institutions(name,lms_type,lms_issuer,deployment_id)
 values('Synthetic','blackboard','https://synthetic.example.test','fixture') returning id into inst;
 insert into public.courses(institution_id,lms_course_id,title)
 values(inst,'synthetic-course','Synthetic') returning id into course;
 insert into public.users(institution_id,lms_user_id,role,pseudonym)
 values(inst,'synthetic-sub','student','synthetic') returning id into canonical;
 insert into public.users(institution_id,lms_user_id,role,pseudonym)
 values(inst,'synthetic-rest','student','synthetic') returning id into legacy;
 insert into public.generated_items(institution_id,course_id,kind,prompt)
 values(inst,course,'flashcard','Synthetic') returning id into item;
 insert into public.item_reviews(institution_id,user_id,course_id,item_id,session_id,
 mode,outcome,was_due,counted,idempotency_key)
 values(inst,canonical,course,item,shared_session,'flashcard','good',true,true,'same-key'),
       (inst,legacy,course,item,shared_session,'flashcard','again',true,true,'same-key');
 -- Even narrowly suspending immutability cannot safely resolve uniqueness.
 begin
  alter table public.item_reviews disable trigger t_immutable;
  update public.item_reviews set user_id=canonical where user_id=legacy;
  raise exception 'expected unique collision';
 exception when unique_violation then blocked := true;
 end;
 if not blocked then raise exception 'collision did not block'; end if;
 if exists(select 1 from pg_trigger where tgrelid='public.item_reviews'::regclass
           and tgname='t_immutable' and tgenabled<>'O') then
  raise exception 'trigger not restored on collision rollback';
 end if;
 -- Isolate the partial session uniqueness from the idempotency constraint.
 begin
  alter table public.item_reviews disable trigger t_immutable;
  update public.item_reviews set idempotency_key='different-key' where user_id=legacy;
  update public.item_reviews set user_id=canonical where user_id=legacy;
  raise exception 'expected session collision';
 exception when unique_violation then null;
 end;
 insert into public.practice_answer_results(institution_id,user_id,course_id,item_id,
 idempotency_key,prompt,choice_id,correct_option_id,correct,mastery_before_level,mastery_after_level)
 values(inst,canonical,course,item,'answer-key','Synthetic','a','a',true,'No evidence','Developing'),
       (inst,legacy,course,item,'answer-key','Synthetic','b','a',false,'No evidence','Developing');
 begin
  alter table public.practice_answer_results disable trigger practice_answer_results_immutable;
  update public.practice_answer_results set user_id=canonical where user_id=legacy;
  raise exception 'expected answer-key collision';
 exception when unique_violation then null;
 end;
 -- Exact resolver contradiction: redirected alias + retained exact legacy key.
 insert into public.lms_identity_aliases(institution_id,lms_user_id,user_id,source)
 values(inst,'synthetic-rest',canonical,'backfill');
 if not exists(select 1 from public.users u join public.lms_identity_aliases a
  on a.institution_id=u.institution_id and a.lms_user_id=u.lms_user_id
  where u.id=legacy and a.user_id<>u.id) then
  raise exception 'expected resolver conflict';
 end if;
 insert into public.evidence_events(institution_id,user_id,course_id,type,correct)
 values(inst,legacy,course,'practice',true) returning id into event_id;
 select count(*) into rows_before from public.audit_log;
 -- Failure after an exact-ID evidence UPDATE rolls back both data and DDL.
 begin
  lock table public.evidence_events in access exclusive mode;
  alter table public.evidence_events disable trigger t_immutable;
  update public.evidence_events set user_id=canonical
   where id=event_id and user_id=legacy and institution_id=inst;
  alter table public.evidence_events enable trigger t_immutable;
  raise exception using errcode='ZX001',message='injected failure';
 exception when sqlstate 'ZX001' then null;
 end;
 if not exists(select 1 from public.evidence_events where id=event_id and user_id=legacy) then
  raise exception 'evidence rollback failed';
 end if;
 if exists(select 1 from pg_trigger where tgrelid='public.evidence_events'::regclass
  and tgname='t_immutable' and tgenabled<>'O') then raise exception 'trigger rollback failed'; end if;
 begin
  update public.evidence_events set user_id=canonical where id=event_id;
  raise exception using errcode='ZX002',message='immutability missing';
 exception when raise_exception then null;
 end;
 if (select count(*) from public.audit_log)<>rows_before then raise exception 'audit changed'; end if;
 if (select count(*) from public.item_reviews where user_id in (canonical,legacy))<>2
 then raise exception 'review history lost'; end if;
 if (select count(*) from public.practice_answer_results where user_id in (canonical,legacy))<>2
 then raise exception 'answer history lost'; end if;
end $$;
rollback;
select 'PASS source-key/session collisions; resolver conflict; exact-ID failure rollback; immutable trigger restored; source counts preserved';
