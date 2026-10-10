-- Atomically reject a live skill and retire every live bank item it owns.
-- Called only from the authenticated API service-role client after its
-- instructor-of-course/admin check. Mastery and evidence are historical facts
-- and are intentionally not modified.
create or replace function public.reject_approved_skill(
  p_institution_id uuid,
  p_course_id uuid,
  p_skill_id uuid,
  p_reviewed_by text
)
returns table (skill_id uuid, retired_items integer)
language plpgsql
set search_path = public
as $$
declare
  changed integer;
begin
  update public.skills s
     set status = 'rejected', reviewed_by = p_reviewed_by, reviewed_at = now()
   where s.id = p_skill_id
     and s.institution_id = p_institution_id
     and s.course_id = p_course_id
     and s.status = 'approved';
  get diagnostics changed = row_count;
  if changed = 0 then
    return;
  end if;

  update public.generated_items g
     set retired_at = now()
   where g.institution_id = p_institution_id
     and g.course_id = p_course_id
     and g.skill_id = p_skill_id
     and g.origin = 'bank'
     and g.retired_at is null;
  get diagnostics retired_items = row_count;
  skill_id := p_skill_id;
  return next;
end;
$$;

revoke all on function public.reject_approved_skill(uuid, uuid, uuid, text) from public, anon, authenticated;
grant execute on function public.reject_approved_skill(uuid, uuid, uuid, text) to service_role;
