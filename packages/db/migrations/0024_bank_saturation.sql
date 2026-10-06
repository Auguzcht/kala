-- Kala — 0024_bank_saturation.sql
-- Persist the point at which a usable skill is saturated by duplicate output.

alter table public.skill_bank_state
  add column if not exists saturated_at timestamptz,
  add column if not exists saturated_depth int;
