-- Card-memory prerequisites: distinguish the most recent card outcome and
-- resolve institution-local day boundaries without changing mastery history.
alter table public.srs_state
  add column if not exists last_outcome text
  check (last_outcome in ('good', 'again'));

update public.srs_state
set last_outcome = case
  when reps = 0 then null
  when streak > 0 then 'good'
  else 'again'
end;

alter table public.institutions
  add column if not exists timezone text not null default 'UTC';

update public.institutions
set timezone = 'Asia/Manila'
where id = '64a59889-ba9c-44ae-87c8-765f86c92c78'
  and lms_issuer = 'https://blackboard.com'
  and deployment_id = '8602f416-6070-4e2d-bdfd-3bda44788fbe';
