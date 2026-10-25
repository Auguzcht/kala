-- WI-25 / TWIN-REQ-010: synthetic-only local Postgres proof after 0001–0037 + 0039.
-- Run in a dedicated throwaway database. The transaction rolls back every fixture.
begin;
insert into public.institutions (id,name,lms_type,lms_issuer,deployment_id)
values ('00000000-0000-0000-0000-000000000001','Synthetic history test','blackboard','synthetic-wi25','synthetic-wi25');
insert into public.users (id,institution_id,lms_user_id,role,pseudonym)
values ('00000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000001','synthetic-wi25','student','Synthetic');
insert into public.courses (id,institution_id,lms_course_id,title)
values ('00000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-000000000001','synthetic-wi25','Synthetic');
insert into public.enrollments (institution_id,user_id,course_id,role)
values ('00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000002',
        '00000000-0000-0000-0000-000000000003','student');
do $$
begin
  if not exists (
    select course_id from public.enrollments
    where institution_id='00000000-0000-0000-0000-000000000001'
    and user_id='00000000-0000-0000-0000-000000000002'
    and course_id='00000000-0000-0000-0000-000000000003' and role='student' limit 1
  ) then raise exception 'own history admission query failed'; end if;
  if exists (
    select course_id from public.enrollments
    where institution_id='00000000-0000-0000-0000-000000000001'
    and user_id='00000000-0000-0000-0000-000000000004'
    and course_id='00000000-0000-0000-0000-000000000003' and role='student' limit 1
  ) then raise exception 'other user admitted'; end if;
end $$;
insert into public.evidence_events (id,institution_id,user_id,course_id,type,correct,created_at)
select lpad(to_hex(n),32,'0')::uuid,'00000000-0000-0000-0000-000000000001',
'00000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000003',
'practice',true,'2026-10-25T12:00:00Z'::timestamptz - ((n/20)::text || ' days')::interval
from generate_series(100,160) n;

-- Exact HTTP query's OR form, including ID ties; compare against native tuple order.
do $$
declare anchor public.evidence_events; actual uuid[]; expected uuid[]; page_count integer;
begin
  select * into anchor from public.evidence_events
  where institution_id='00000000-0000-0000-0000-000000000001'
  and user_id='00000000-0000-0000-0000-000000000002'
  and course_id='00000000-0000-0000-0000-000000000003'
  order by created_at desc,id desc offset 24 limit 1;
  select array_agg(id order by created_at desc,id desc) into actual from (
    select id,created_at from public.evidence_events
    where institution_id='00000000-0000-0000-0000-000000000001'
    and user_id='00000000-0000-0000-0000-000000000002'
    and course_id='00000000-0000-0000-0000-000000000003'
    and (created_at < anchor.created_at or (created_at=anchor.created_at and id<anchor.id))
    order by created_at desc,id desc limit 26
  ) p;
  select array_agg(id order by created_at desc,id desc) into expected from (
    select id,created_at from public.evidence_events
    where user_id='00000000-0000-0000-0000-000000000002'
    and course_id='00000000-0000-0000-0000-000000000003'
    and (created_at,id)<(anchor.created_at,anchor.id)
    order by created_at desc,id desc limit 26
  ) p;
  if actual is distinct from expected or cardinality(actual)<>26 then
    raise exception 'history keyset mismatch';
  end if;
  select count(*) into page_count from public.evidence_events
  where user_id='00000000-0000-0000-0000-000000000002'
  and course_id='00000000-0000-0000-0000-000000000003';
  if page_count<>61 then raise exception 'fixture count mismatch'; end if;
  raise notice 'WI-25 synthetic keyset: equal timestamp ordering and 26-row lookahead passed';
end $$;
set local enable_seqscan=off;
explain (costs off)
select id,created_at from public.evidence_events
where institution_id='00000000-0000-0000-0000-000000000001'
and user_id='00000000-0000-0000-0000-000000000002'
and course_id='00000000-0000-0000-0000-000000000003'
order by created_at desc,id desc limit 26;
rollback;
