-- Pair 1: one-sided history. Pair 2: both sides with safe state collisions.
insert into public.institutions(id,name,lms_type,lms_issuer,deployment_id)
select distinct institution_id,'Synthetic','blackboard','https://fixture.example.test','fixture' from wi24_pairs;
insert into public.courses(id,institution_id,lms_course_id,title)
select distinct unnest(course_ids),institution_id,'fixture-course','Synthetic' from wi24_pairs;
insert into public.users(id,institution_id,lms_user_id,role,pseudonym)
select canonical_id,institution_id,lms_uuid,'student','Synthetic' from wi24_pairs
union all select legacy_id,institution_id,'legacy-'||label,'student','Synthetic' from wi24_pairs;
insert into public.lms_identity_aliases(institution_id,lms_user_id,user_id,source)
select institution_id,lms_uuid,canonical_id,'launch' from wi24_pairs
union all select institution_id,'legacy-'||label,legacy_id,'roster' from wi24_pairs;
insert into public.enrollments(institution_id,user_id,course_id,role)
select institution_id,canonical_id,course_ids[1],'student' from wi24_pairs
union all select institution_id,legacy_id,course_ids[1],'student' from wi24_pairs;
insert into public.skills(institution_id,course_id,name,bloom_level,status)
select institution_id,course_ids[1],'Synthetic','remember','approved' from wi24_pairs group by institution_id,course_ids;
insert into public.generated_items(institution_id,course_id,skill_id,kind,prompt)
select institution_id,course_id,id,'flashcard','Synthetic' from public.skills;
insert into public.quiz_sets(institution_id,course_id,skill_id,kind,size)
select institution_id,course_id,id,'practice',1 from public.skills;
insert into public.evidence_events(institution_id,user_id,course_id,skill_id,type,correct,created_at)
select p.institution_id,p.legacy_id,p.course_ids[1],s.id,'practice',true,'2020-01-01T01:02:03.123456Z'::timestamptz from wi24_pairs p
join public.skills s on s.course_id=p.course_ids[1]
union all select p.institution_id,p.canonical_id,p.course_ids[1],s.id,'practice',false,'2020-01-02T01:02:03.123456Z'::timestamptz from wi24_pairs p
join public.skills s on s.course_id=p.course_ids[1] where p.label=2;
insert into public.mastery_state(institution_id,user_id,course_id,skill_id,estimate)
select e.institution_id,e.user_id,e.course_id,e.skill_id,0.6 from public.evidence_events e;
insert into public.readiness_snapshots(institution_id,user_id,course_id,score)
select e.institution_id,e.user_id,e.course_id,0.6 from public.evidence_events e;
insert into public.srs_state(institution_id,user_id,course_id,item_id,skill_id,box,last_reviewed_at)
select e.institution_id,e.user_id,e.course_id,i.id,i.skill_id,
 case when e.user_id=p.legacy_id then 3 else 1 end,
 case when e.user_id=p.legacy_id then '2020-03-01'::timestamptz else '2020-02-01'::timestamptz end
from public.evidence_events e join wi24_pairs p on e.user_id in(p.canonical_id,p.legacy_id)
join public.generated_items i on i.course_id=e.course_id;
insert into public.quiz_set_attempts(institution_id,user_id,course_id,set_id,attempt_number,completed_at)
select e.institution_id,e.user_id,e.course_id,q.id,1,'2020-01-03' from public.evidence_events e
join public.quiz_sets q on q.course_id=e.course_id;
insert into public.practice_answer_results(institution_id,user_id,course_id,item_id,set_id,attempt_id,
 idempotency_key,prompt,choice_id,correct_option_id,correct,xp_awarded,mastery_before_level,mastery_after_level)
select a.institution_id,a.user_id,a.course_id,i.id,a.set_id,a.id,'answer-'||a.user_id,'Synthetic','a','a',true,12,'Developing','Proficient'
from public.quiz_set_attempts a join public.generated_items i on i.course_id=a.course_id;
insert into public.item_reviews(institution_id,user_id,course_id,item_id,session_id,mode,outcome,was_due,counted,idempotency_key)
select e.institution_id,e.user_id,e.course_id,i.id,gen_random_uuid(),'quiz','good',true,true,'review-'||e.user_id
from public.evidence_events e join public.generated_items i on i.course_id=e.course_id;
insert into public.item_exposures(institution_id,user_id,course_id,item_id,skill_id,times_tested,last_answered_at,last_correct)
select e.institution_id,e.user_id,e.course_id,i.id,i.skill_id,1,e.created_at,e.correct
from public.evidence_events e join public.generated_items i on i.course_id=e.course_id;
insert into public.tutor_conversations(institution_id,user_id,course_id,title)
select institution_id,legacy_id,course_ids[1],'Synthetic' from wi24_pairs;
insert into public.tutor_messages(conversation_id,role,content)
select id,'user','Synthetic' from public.tutor_conversations;
insert into public.recommendations(institution_id,user_id,course_id,action)
select institution_id,legacy_id,course_ids[1],'Synthetic' from wi24_pairs;
-- Identity metadata and historical actor/launch references remain unchanged.
insert into public.user_profiles(user_id,display_name,email)
select canonical_id,'Synthetic','fixture@example.test' from wi24_pairs
union all select legacy_id,'Synthetic','fixture@example.test' from wi24_pairs;
insert into public.lti_launches(institution_id,user_id,course_id,role,message_type)
select institution_id,legacy_id,course_ids[1],'student','Synthetic' from wi24_pairs;
insert into public.audit_log(institution_id,actor_id,actor_role,action,metadata)
select institution_id,legacy_id,'student','SYNTHETIC_HISTORY',jsonb_build_object('user_id',legacy_id) from wi24_pairs;
update public.skills s set reviewed_by=p.lms_uuid from wi24_pairs p where p.label=1 and s.course_id=p.course_ids[1];
update public.recommendations r set decided_by=p.legacy_id from wi24_pairs p where r.user_id=p.legacy_id;
insert into public.tutor_conversations(institution_id,user_id,course_id,title)
select institution_id,canonical_id,course_ids[1],'Synthetic canonical' from wi24_pairs;
insert into public.tutor_attachments(institution_id,user_id,conversation_id,storage_path,filename,mime_type,size_bytes)
select c.institution_id,c.user_id,c.id,'synthetic/canonical/file','Synthetic','text/plain',1
from public.tutor_conversations c join wi24_pairs p on c.user_id=p.canonical_id;
