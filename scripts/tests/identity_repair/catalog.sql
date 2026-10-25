-- Metadata only: no application rows or identifiers.
select 'COLUMN', c.relname,a.attname,format_type(a.atttypid,a.atttypmod)
from pg_attribute a join pg_class c on c.oid=a.attrelid
join pg_namespace n on n.oid=c.relnamespace
where n.nspname='public' and c.relkind='r' and a.attnum>0 and not a.attisdropped
order by 2,3;
select 'CONSTRAINT',c.relname,k.conname,pg_get_constraintdef(k.oid)
from pg_constraint k join pg_class c on c.oid=k.conrelid
join pg_namespace n on n.oid=c.relnamespace
where n.nspname='public' and k.contype in ('p','u','f') order by 2,3;
select 'INDEX',tablename,indexname,indexdef from pg_indexes
where schemaname='public' and indexdef like 'CREATE UNIQUE%' order by 2,3;
select 'TRIGGER',c.relname,t.tgname,pg_get_triggerdef(t.oid)
from pg_trigger t join pg_class c on c.oid=t.tgrelid
join pg_namespace n on n.oid=c.relnamespace
where n.nspname='public' and not t.tgisinternal order by 2,3;
