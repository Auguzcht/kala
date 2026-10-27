"""INSTR-REQ-012 synthetic count-query proof on real local PostgreSQL.

No ports, network, application configuration, credentials or hosted access.
Minimal table shapes test SQL/counts, not migrations, RLS or real identities.
"""
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

IMAGE = 'public.ecr.aws/supabase/postgres:17.6.1.139'
CONTAINER = 'kala-standing-counts-' + uuid.uuid4().hex[:10]
ENV = {'PATH': os.environ['PATH']}


def docker(*args, source=None, check=True):
    result = subprocess.run(['docker', *args], input=source, text=True,
                            capture_output=True, env=ENV, timeout=60)
    if check and result.returncode:
        raise RuntimeError('Local count-query proof failed, raw output suppressed')
    return result


def sql(source, check=True):
    return docker('exec', '-i', CONTAINER, 'psql', '-X', '-U', 'supabase_admin',
                  '-d', 'standing_counts', '-v', 'ON_ERROR_STOP=1', '-Atq',
                  source=source, check=check)


def uid(n):
    return f'10000000-0000-4000-8000-{n:012d}'


created = False
try:
    docker('run', '--detach', '--pull=never', '--network', 'none', '--name', CONTAINER,
           '--env', 'POSTGRES_HOST_AUTH_METHOD=trust', IMAGE)
    created = True
    for _ in range(150):
        if docker('inspect', '--format', '{{.State.Health.Status}}', CONTAINER).stdout.strip() == 'healthy':
            break
        time.sleep(0.2)
    else:
        raise RuntimeError('Local PostgreSQL health timeout')
    docker('exec', CONTAINER, 'psql', '-X', '-U', 'supabase_admin', '-d', 'postgres',
           '-c', 'create database standing_counts;')
    sql('''
      create table users(id uuid primary key, institution_id uuid, role text, lms_user_id text);
      create table enrollments(user_id uuid, institution_id uuid, course_id uuid, role text);
      create table lms_identity_aliases(institution_id uuid, lms_user_id text, user_id uuid);
      create table skills(id uuid primary key, institution_id uuid, course_id uuid, status text,
                          created_at timestamptz, reviewed_at timestamptz);
      create table mastery_state(user_id uuid, institution_id uuid, course_id uuid,
                                 skill_id uuid, estimate numeric, attempts integer);
      create table evidence_events(id uuid primary key, user_id uuid, institution_id uuid,
                                   course_id uuid, correct boolean, hints_used integer,
                                   created_at timestamptz);
    ''')
    for n in range(1, 28):
        sql(f"insert into users values ('{uid(n)}','{uid(100)}','student','synthetic-{n}');")
        if n <= 25:
            sql(f"insert into enrollments values ('{uid(n)}','{uid(100)}','{uid(101)}','student');")
    for n in range(1, 16):
        sql(f"insert into skills values ('{uid(200+n)}','{uid(100)}','{uid(101)}','approved','2026-10-01','2026-10-25');")
        if n <= 11:
            sql(f"insert into mastery_state values ('{uid(1)}','{uid(100)}','{uid(101)}','{uid(200+n)}',0.73949,{371 if n == 1 else 1});")
        if n <= 7:
            sql(f"insert into mastery_state values ('{uid(2)}','{uid(100)}','{uid(101)}','{uid(200+n)}',0.55,{7 if n == 1 else 1});")
    sql(f"""insert into evidence_events
      select gen_random_uuid(), '{uid(1)}'::uuid, '{uid(100)}'::uuid, '{uid(101)}'::uuid,
        case when n <= 20 then n % 10 between 1 and 7
             when n <= 200 then n <= 144 else n <= 348 end,
        0, '2026-10-27'::timestamptz - n * interval '1 second'
      from generate_series(1,381) n;
      insert into evidence_events
      select gen_random_uuid(), '{uid(2)}'::uuid, '{uid(100)}'::uuid, '{uid(101)}'::uuid,
        n <= 9, 0, '2026-10-27'::timestamptz - (500+n) * interval '1 second'
      from generate_series(1,13) n;
      insert into evidence_events values (gen_random_uuid(),'{uid(1)}','{uid(999)}','{uid(101)}',false,99,now());
      insert into evidence_events values (gen_random_uuid(),'{uid(1)}','{uid(100)}','{uid(999)}',false,99,now());
    """)
    template = Path(__file__).with_name('learner-counts.readonly.sql').read_text()
    replacements = {'institution_id':100, 'course_id':101, 'hanna_canonical':1,
                    'hanna_legacy':26, 'alfred_canonical':2, 'alfred_legacy':27,
                    'roster_target':1, 'drawer_target':1}

    def query(overrides=None):
        source = template
        for name, number in (replacements | (overrides or {})).items():
            source = source.replace(f'NULL::uuid as {name}', f"'{uid(number)}'::uuid as {name}")
        return json.loads(sql(source).stdout)

    result = query()
    gate = result['identity_gate']
    assert gate['required_inputs_set'] == 1
    assert gate['anchors_supplied'] == gate['anchors_found_in_institution'] == 4
    assert gate['canonical_learners_enrolled'] == 2
    assert all(gate[k] == 0 for k in gate if k.startswith(('cross_', 'targets_', 'roster_', 'drawer_')))
    assert result['anchor_counts']['hanna_canonical']['approved_mastery_attempts'] == 381
    assert result['anchor_counts']['hanna_canonical']['evidence'] == 381
    assert result['anchor_counts']['alfred_canonical']['evidence'] == 13
    windows = result['windows']
    assert (windows['roster_correct'], windows['roster_graded']) == (286, 381)
    assert (windows['drawer_correct'], windows['drawer_graded']) == (138, 200)
    assert (windows['recent_correct'], windows['recent_graded']) == (7, 10)
    assert (windows['prior_correct'], windows['prior_graded']) == (7, 10)
    assert result['course_counts']['enrolled_learners'] == 25
    assert result['course_counts']['measured_learners'] == 2
    assert result['course_counts']['learners_above_hanna'] == 0
    assert result['course_counts']['approved_skills'] == 15
    wrong = query({'drawer_target':2})['identity_gate']
    assert wrong['targets_not_hanna_canonical'] == 1 and wrong['drawer_alfred_owned_events'] == 13
    collision = query({'alfred_legacy':1})['identity_gate']
    assert collision['cross_family_anchor_collisions'] == 1
    sql(f"insert into lms_identity_aliases values ('{uid(100)}','synthetic-1','{uid(2)}');")
    assert query()['identity_gate']['cross_family_alias_owners'] == 1
    sql('delete from lms_identity_aliases;')
    sql(f"""insert into evidence_events select gen_random_uuid(), '{uid(3)}'::uuid,
      '{uid(100)}'::uuid, '{uid(101)}'::uuid, null, 0, '2026-10-28'::timestamptz + n * interval '1 second'
      from generate_series(1,2100) n;""")
    capped = query()['windows']
    assert capped['class_events_loaded'] == 2000 and capped['roster_events'] == 0
    assert capped['drawer_graded'] == 200
    assert json.loads(sql(template).stdout)['identity_gate']['required_inputs_set'] == 0
    denied = sql('begin read only; insert into users(id) values(gen_random_uuid()); rollback;', check=False)
    assert denied.returncode != 0 and 'read-only transaction' in denied.stderr
    version = sql("select current_setting('server_version');").stdout.strip()
    print(f'INSTR-REQ-012 counts query passed on local PostgreSQL {version}: independent windows, neutral momentum counts, course scope, wrong target, anchor collision, cross-alias owner, cap and read-only checks. Synthetic only.')
finally:
    if created:
        docker('rm', '--force', CONTAINER, check=False)
