-- Similarity search for RAG, scoped to an institution + course. Called by the
-- backend via PostgREST rpc('match_content_items', ...). SECURITY DEFINER so
-- the service path can search; callers still pass the scope explicitly.
create or replace function public.match_content_items(
  p_institution_id uuid,
  p_course_id uuid,
  p_query vector(1024),
  p_match_count int default 5
)
returns table (id uuid, skill_id uuid, chunk_text text, similarity float)
language sql stable
set search_path = public, extensions
as $$
  select ci.id, ci.skill_id, ci.chunk_text,
         1 - (ci.embedding <=> p_query) as similarity
  from public.content_items ci
  where ci.institution_id = p_institution_id
    and ci.course_id = p_course_id
    and ci.embedding is not null
  order by ci.embedding <=> p_query
  limit p_match_count
$$;
