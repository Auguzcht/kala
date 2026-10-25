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
