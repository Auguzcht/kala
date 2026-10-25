-- Synthetic only. Run by wi26_rls_local.py in its private local database.
insert into public.users(id,institution_id,lms_user_id,role,pseudonym)
select ('20000000-0000-4000-8000-' || lpad(n::text,12,'0'))::uuid,
       ('10000000-0000-4000-8000-' || lpad((case when n>=5 then 2 else 1 end)::text,12,'0'))::uuid,
       'synthetic-'||n, case when n=1 then 'student' when n in (4,6) then 'admin' else 'instructor' end,
       'Synthetic '||n
from generate_series(1,6) n;
insert into public.courses(id,institution_id,lms_course_id,title) values
('30000000-0000-4000-8000-000000000001','10000000-0000-4000-8000-000000000001','synthetic-a','Synthetic A'),
('30000000-0000-4000-8000-000000000002','10000000-0000-4000-8000-000000000001','synthetic-b','Synthetic B');
insert into public.enrollments(institution_id,user_id,course_id,role) values
('10000000-0000-4000-8000-000000000001','20000000-0000-4000-8000-000000000001','30000000-0000-4000-8000-000000000001','student'),
('10000000-0000-4000-8000-000000000001','20000000-0000-4000-8000-000000000002','30000000-0000-4000-8000-000000000001','instructor'),
('10000000-0000-4000-8000-000000000001','20000000-0000-4000-8000-000000000003','30000000-0000-4000-8000-000000000002','instructor');
insert into public.recommendations(institution_id,user_id,course_id,action,status)
select '10000000-0000-4000-8000-000000000001','20000000-0000-4000-8000-000000000001',
       '30000000-0000-4000-8000-000000000001','practice',s
from unnest(array['suggested','approved','modified','rejected','completed']) s;

-- Extended staff-boundary proof: an unrelated learner/course and shared material.
insert into public.users(id,institution_id,lms_user_id,role,pseudonym) values
('20000000-0000-4000-8000-000000000007','10000000-0000-4000-8000-000000000001','synthetic-7','student','Synthetic 7'),
('20000000-0000-4000-8000-000000000008','10000000-0000-4000-8000-000000000001','synthetic-8','student','Synthetic 8');
insert into public.enrollments(institution_id,user_id,course_id,role) values
('10000000-0000-4000-8000-000000000001','20000000-0000-4000-8000-000000000007','30000000-0000-4000-8000-000000000002','student');
insert into public.skills(id,institution_id,course_id,name,bloom_level,status)
select ('40000000-0000-4000-8000-'||lpad(n::text,12,'0'))::uuid,
       '10000000-0000-4000-8000-000000000001',
       ('30000000-0000-4000-8000-'||lpad(n::text,12,'0'))::uuid,
       'Synthetic skill '||n,'apply','approved'
from generate_series(1,2) n;
insert into public.generated_items(id,institution_id,course_id,skill_id,kind,prompt)
select ('50000000-0000-4000-8000-'||lpad(n::text,12,'0'))::uuid,
       '10000000-0000-4000-8000-000000000001',
       ('30000000-0000-4000-8000-'||lpad(n::text,12,'0'))::uuid,
       ('40000000-0000-4000-8000-'||lpad(n::text,12,'0'))::uuid,'practice','Synthetic prompt'
from generate_series(1,2) n;
insert into public.quiz_sets(id,institution_id,course_id,skill_id,kind,size)
select ('60000000-0000-4000-8000-'||lpad(n::text,12,'0'))::uuid,
       '10000000-0000-4000-8000-000000000001',
       ('30000000-0000-4000-8000-'||lpad(n::text,12,'0'))::uuid,
       ('40000000-0000-4000-8000-'||lpad(n::text,12,'0'))::uuid,'practice',1
from generate_series(1,2) n;
insert into public.quiz_set_items(set_id,item_id,position)
select ('60000000-0000-4000-8000-'||lpad(n::text,12,'0'))::uuid,
       ('50000000-0000-4000-8000-'||lpad(n::text,12,'0'))::uuid,0
from generate_series(1,2) n;
insert into public.evidence_events(institution_id,user_id,course_id,skill_id,type,correct)
select s.institution_id, e.user_id, s.course_id, s.id, 'practice', true
from public.skills s join public.enrollments e on e.course_id=s.course_id and e.role='student';
insert into public.mastery_state(institution_id,user_id,course_id,skill_id,estimate,attempts)
select s.institution_id, e.user_id, s.course_id, s.id,0.6,1
from public.skills s join public.enrollments e on e.course_id=s.course_id and e.role='student';
insert into public.readiness_snapshots(institution_id,user_id,course_id,score)
select institution_id,user_id,course_id,0.6 from public.enrollments where role='student';
insert into public.srs_state(institution_id,user_id,course_id,skill_id,item_id)
select s.institution_id,e.user_id,s.course_id,s.id,g.id from public.skills s
join public.enrollments e on e.course_id=s.course_id and e.role='student'
join public.generated_items g on g.skill_id=s.id;
insert into public.quiz_set_attempts(institution_id,user_id,course_id,set_id)
select q.institution_id,e.user_id,q.course_id,q.id from public.quiz_sets q
join public.enrollments e on e.course_id=q.course_id and e.role='student';
insert into public.item_exposures(institution_id,user_id,course_id,skill_id,item_id)
select s.institution_id,e.user_id,s.course_id,s.id,g.id from public.skills s
join public.enrollments e on e.course_id=s.course_id and e.role='student'
join public.generated_items g on g.skill_id=s.id;
insert into public.item_reviews(institution_id,user_id,course_id,skill_id,item_id,mode,outcome,was_due,counted,idempotency_key)
select s.institution_id,e.user_id,s.course_id,s.id,g.id,'quiz','good',false,true,'synthetic-'||g.id from public.skills s
join public.enrollments e on e.course_id=s.course_id and e.role='student'
join public.generated_items g on g.skill_id=s.id;
insert into public.content_items(institution_id,course_id,chunk_text)
select institution_id,id,'Synthetic content' from public.courses;
insert into public.assessments(institution_id,course_id,title)
select institution_id,id,'Synthetic assessment' from public.courses;
insert into public.ingest_jobs(institution_id,course_id)
select institution_id,id from public.courses;
insert into public.guided_lessons(id,institution_id,course_id,skill_id,title)
select ('70000000-0000-4000-8000-'||right(id::text,12))::uuid,
       institution_id,course_id,id,'Synthetic lesson' from public.skills;
insert into public.guided_lesson_steps(lesson_id,position,summary)
select id,0,'Synthetic summary' from public.guided_lessons;
insert into public.lms_identity_aliases(institution_id,user_id,lms_user_id)
select institution_id,id,lms_user_id from public.users;
insert into public.researchers(id,email) values
('20000000-0000-4000-8000-000000000099','synthetic-researcher@example.invalid');
insert into public.researcher_grants(researcher_id,institution_id,scope,expires_at) values
('20000000-0000-4000-8000-000000000099','10000000-0000-4000-8000-000000000001','row_anon',now()+interval '1 day');
insert into public.consents(institution_id,user_id,granted,policy_version) values
('10000000-0000-4000-8000-000000000001','20000000-0000-4000-8000-000000000001',true,'synthetic');

insert into public.user_profiles(user_id,display_name)
select id,'Synthetic profile' from public.users;
