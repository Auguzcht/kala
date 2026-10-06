-- Replace the model-backed content tag with an idempotent, auditable
-- embedding decision. The worker/API call the function once per course;
-- Postgres performs the chunk x approved-skill comparison in one statement.
alter table public.content_items
  add column if not exists tag_score numeric,
  add column if not exists tag_margin numeric,
  add column if not exists tag_method text check (tag_method in ('llm', 'embedding')),
  add column if not exists tag_ambiguous boolean not null default false;

create or replace function public.recompute_embedding_tags(
  p_course_id uuid,
  p_threshold numeric default 0.544,
  p_min_margin numeric default 0.03
)
returns table (
  tagged bigint,
  below_threshold bigint,
  ambiguous bigint,
  changed bigint,
  gap_filled bigint
)
language plpgsql
set search_path = public, extensions
as $$
declare
  updated_count bigint;
  filled_count bigint;
begin
  create temporary table _embedding_tag_decisions on commit drop as
  with ranked as (
    select
      ci.id as content_id,
      s.id as skill_id,
      s.module_ref,
      1 - (ci.embedding <=> s.embedding) as score,
      row_number() over (partition by ci.id order by ci.embedding <=> s.embedding) as rank,
      count(*) over (partition by ci.id) as skill_count
    from public.content_items ci
    join public.skills s
      on s.course_id = ci.course_id
     and s.institution_id = ci.institution_id
     and s.status = 'approved'
     and s.embedding is not null
    where ci.course_id = p_course_id
      and ci.embedding is not null
  ), summary as (
    select
      content_id,
      (array_agg(skill_id order by rank))[1] as top_skill_id,
      (array_agg(module_ref order by rank))[1] as top_module_ref,
      max(score) filter (where rank = 1) as top_score,
      (array_agg(module_ref order by rank))[2] as second_module_ref,
      max(score) filter (where rank = 2) as second_score,
      max(skill_count) as skill_count
    from ranked
    group by content_id
  ), decisions as (
    select
      ci.id as content_id,
      ci.skill_id as old_skill_id,
      s.top_skill_id,
      s.top_score,
      case
        when s.top_score is null then null
        when s.skill_count = 1 then s.top_score
        else s.top_score - coalesce(s.second_score, 0)
      end as tag_margin,
      case
        when s.top_score is null or s.top_score < p_threshold then null
        when s.skill_count = 1 then s.top_skill_id
        when s.top_score - coalesce(s.second_score, 0) >= p_min_margin then s.top_skill_id
        when s.top_module_ref is not null and s.top_module_ref = s.second_module_ref then s.top_skill_id
        else null
      end as new_skill_id,
      case
        when s.top_score >= p_threshold
         and s.skill_count > 1
         and s.top_score - coalesce(s.second_score, 0) < p_min_margin
         and not (s.top_module_ref is not null and s.top_module_ref = s.second_module_ref)
        then true
        else false
      end as tag_ambiguous
    from public.content_items ci
    left join summary s on s.content_id = ci.id
    where ci.course_id = p_course_id
      and ci.embedding is not null
  )
  select * from decisions;

  select count(*) into updated_count
  from _embedding_tag_decisions
  where old_skill_id is distinct from new_skill_id;

  update public.content_items ci
     set skill_id = d.new_skill_id,
         tag_score = d.top_score,
         tag_margin = d.tag_margin,
         tag_method = 'embedding',
         tag_ambiguous = d.tag_ambiguous,
         tag_attempted_at = now()
    from _embedding_tag_decisions d
   where ci.id = d.content_id;

  with module_counts as (
    select ci.skill_id, ci.module_ref, count(*) as module_count
      from public.content_items ci
     where ci.course_id = p_course_id
       and ci.skill_id is not null
       and ci.module_ref is not null
     group by ci.skill_id, ci.module_ref
  ), best_modules as (
    select skill_id, module_ref,
           row_number() over (partition by skill_id order by module_count desc, module_ref) as rank
      from module_counts
  )
  update public.skills s
     set module_ref = b.module_ref
    from best_modules b
   where s.id = b.skill_id
     and s.course_id = p_course_id
     and s.module_ref is null
     and b.rank = 1;
  get diagnostics filled_count = row_count;

  return query
  select
    count(*) filter (where new_skill_id is not null),
    count(*) filter (where top_score is null or top_score < p_threshold),
    count(*) filter (where tag_ambiguous),
    updated_count,
    filled_count
  from _embedding_tag_decisions;
end;
$$;
