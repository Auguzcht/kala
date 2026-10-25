"""Fresh real local Postgres proof. No app configuration/imports or dotenv."""
from pathlib import Path
import importlib.util
import json
import os
import shutil
import subprocess
import time
import uuid
import sys
from application_adapters import LocalDB, resolver, worker

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location("repair_identity_split", ROOT / "scripts/repair_identity_split.py")
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


def run():
    container = "kala-wi24-full-" + uuid.uuid4().hex[:12]
    env = {"PATH": os.environ["PATH"], "PYTHON_DOTENV_DISABLED": "1"}
    private = ROOT / "tmp" / ("wi24-" + uuid.uuid4().hex)
    private.mkdir(mode=0o700, parents=True)
    created = False
    db = local = None

    def docker(*args):
        result = subprocess.run(["docker", *args], capture_output=True, env=env, timeout=60)
        if result.returncode:
            raise AssertionError("local Docker fixture failed; details suppressed")
        return result.stdout.decode().strip()

    try:
        docker("run", "--detach", "--pull=never", "--name", container,
               "--publish", "127.0.0.1::5432", "--env", "POSTGRES_HOST_AUTH_METHOD=trust",
               "public.ecr.aws/supabase/postgres:17.6.1.158")
        created = True
        for _ in range(150):
            if docker("inspect", "--format", "{{.State.Health.Status}}", container) == "healthy":
                break
            time.sleep(0.2)
        else:
            raise AssertionError("local fixture startup timeout")
        hba = docker("exec", container, "psql", "-U", "postgres", "-Atqc", "SHOW hba_file")
        docker("exec", container, "sed", "-i", "1ihost all all 0.0.0.0/0 trust", hba)
        docker("exec", container, "psql", "-U", "postgres", "-Atqc", "SELECT pg_reload_conf()")
        port = docker("port", container, "5432/tcp").split(":")[-1]
        for name in ("wi24_source", "wi24_backup", "wi24_restore"):
            docker("exec", container, "createdb", "-U", "postgres", "-T", "template0", name)
        servicefile = private / "services.conf"
        servicefile.write_text("".join(f"[{name}]\nhost=127.0.0.1\nport={port}\nuser=postgres\ndbname={name}\nsslmode=disable\n" for name in ("wi24_source", "wi24_backup", "wi24_restore")))
        servicefile.chmod(0o600)
        env["PGSERVICEFILE"] = str(servicefile)
        probe = subprocess.run(["psql", "-X", "--no-password", "--dbname", "service=wi24_source", "-Atqc", "SELECT 1"], env=env, capture_output=True)
        if probe.returncode:
            # This fixture has synthetic configuration only, never user input.
            raise AssertionError("synthetic connection probe failed; raw error suppressed")
        db = repair.Psql("wi24_source", env=env)
        local = repair.Psql("wi24_backup", env=env)
        db.run((HERE / "bootstrap.sql").read_text())
        for migration in sorted((ROOT / "packages/db/migrations").glob("*.sql")):
            if int(migration.name[:4]) <= 37:
                db.run(migration.read_text())
        columns = repair.schema(db)
        inst, course = str(uuid.uuid4()), str(uuid.uuid4())
        pairs = [{"institution_id": inst, "canonical_id": str(uuid.uuid4()), "legacy_id": str(uuid.uuid4()),
                  "lms_uuid": "synthetic-sub-" + str(n), "lti_sub": "synthetic-sub-" + str(n),
                  "course_ids": [course]} for n in (1, 2)]
        inputfile = private / "pairs.json"
        inputfile.write_text(json.dumps(pairs)); inputfile.chmod(0o600)
        pairs = repair.read_pairs(inputfile)
        repair.create_pairs(db, pairs, private)
        for number, statement in enumerate((HERE / "supported.sql").read_text().split(";"), 1):
            if statement.strip():
                try:
                    db.run(statement + ";")
                except repair.Refused:
                    raise AssertionError(f"synthetic statement {number} failed; payload suppressed") from None
        connection = LocalDB(db, repair.literal)
        resolve = resolver(ROOT, connection)
        for pair in pairs:
            assert resolve(institution_id=inst,lms_user_id=pair["lms_uuid"],role="student",display_name=None,email=None)["id"] == pair["canonical_id"]
            assert resolve(institution_id=inst,lms_user_id="legacy-"+str(pair["label"]),role="student",display_name=None,email=None)["id"] == pair["legacy_id"]
        def cli(name, flags=(), *, expected=0, directory=None, extra_env=None, worker_config=True):
            flags=list(flags)
            if "--apply" in flags and worker_config:
                flags.extend(["--worker-tracer-k","0.15","--confirm-worker-config"])
            outputdir = directory or private / name
            result = subprocess.run([sys.executable,str(ROOT / "scripts/repair_identity_split.py"),
                "--input",str(inputfile),"--source-service","wi24_source","--private-directory",str(outputdir),*flags],
                env=env | (extra_env or {}),capture_output=True,timeout=60)
            assert result.returncode == expected, "public CLI failed: " + result.stdout.decode()
            text = result.stdout.decode()
            assert not result.stderr, "CLI printed raw stderr"
            for pair in pairs:
                assert pair["canonical_id"] not in text and pair["legacy_id"] not in text and inst not in text
            assert "Synthetic" not in text and "synthetic-sub" not in text
            return text
        cli("single-flag",["--apply"],expected=2)
        cli("dry")
        # Unsafe source key on pair 2 must block the whole transaction, pair 1 included.
        db.run("ALTER TABLE public.item_reviews DISABLE TRIGGER t_immutable; "
               "UPDATE public.item_reviews l SET idempotency_key=c.idempotency_key FROM public.item_reviews c,wi24_pairs p "
               "WHERE p.label=2 AND l.user_id=p.legacy_id AND c.user_id=p.canonical_id; "
               "ALTER TABLE public.item_reviews ENABLE TRIGGER t_immutable;")
        blocked_before = repair.snapshot(db)
        text = cli("blocked-key",["--apply","--confirm","--backup-service","wi24_backup"],expected=2)
        assert "SOURCE_KEY_COLLISION" in text and repair.snapshot(db)==blocked_before
        db.run("ALTER TABLE public.item_reviews DISABLE TRIGGER t_immutable; "
               "UPDATE public.item_reviews SET idempotency_key='review-'||user_id; "
               "UPDATE public.item_reviews l SET session_id=c.session_id FROM public.item_reviews c,wi24_pairs p "
               "WHERE p.label=2 AND l.user_id=p.legacy_id AND c.user_id=p.canonical_id; "
               "ALTER TABLE public.item_reviews ENABLE TRIGGER t_immutable;")
        blocked_before = repair.snapshot(db)
        assert "SOURCE_SESSION_COLLISION" in cli("blocked-session",["--apply","--confirm"],expected=2)
        assert repair.snapshot(db)==blocked_before
        db.run("ALTER TABLE public.item_reviews DISABLE TRIGGER t_immutable; "
               "UPDATE public.item_reviews SET session_id=gen_random_uuid(); "
               "ALTER TABLE public.item_reviews ENABLE TRIGGER t_immutable;")
        db.run("CREATE TEMP TABLE before_ambiguous AS SELECT * FROM public.evidence_events; "
               "ALTER TABLE public.evidence_events DISABLE TRIGGER t_immutable; "
               "UPDATE public.evidence_events e SET created_at='2020-01-01T01:02:03.123456Z' FROM wi24_pairs p "
               "WHERE p.label=2 AND e.user_id=p.canonical_id; ALTER TABLE public.evidence_events ENABLE TRIGGER t_immutable;")
        ambiguous=repair.snapshot(db)
        assert "AMBIGUOUS_WORKER_ORDER" in cli("ambiguous",["--apply","--confirm"],expected=2)
        assert repair.snapshot(db)==ambiguous
        db.run("ALTER TABLE public.evidence_events DISABLE TRIGGER t_immutable; "
               "UPDATE public.evidence_events e SET created_at=b.created_at FROM before_ambiguous b WHERE e.id=b.id; "
               "ALTER TABLE public.evidence_events ENABLE TRIGGER t_immutable;")
        def guard_case(name, setup, reset, reason):
            db.run(setup)
            protected=repair.snapshot(db)
            assert reason in cli(name,["--apply","--confirm"],expected=2)
            assert repair.snapshot(db)==protected
            db.run(reset)
        guard_case("profile-conflict", "UPDATE public.user_profiles t SET display_name='Unequal synthetic' FROM wi24_pairs p WHERE t.user_id=p.legacy_id;",
                   "UPDATE public.user_profiles SET display_name='Synthetic';", "PROFILE_CONFLICT")
        guard_case("consent", "INSERT INTO public.consents(institution_id,user_id,granted,policy_version) SELECT institution_id,legacy_id,true,'synthetic' FROM wi24_pairs;",
                   "DELETE FROM public.consents WHERE policy_version='synthetic';", "CONSENT_PRESENT")
        guard_case("dsr", "INSERT INTO public.data_subject_requests(institution_id,user_id,kind) SELECT institution_id,legacy_id,'export' FROM wi24_pairs;",
                   "DELETE FROM public.data_subject_requests;", "DSR_PRESENT")
        guard_case("legacy-attachment", "INSERT INTO public.tutor_attachments(institution_id,user_id,conversation_id,storage_path,filename,mime_type,size_bytes) "
                   "SELECT c.institution_id,c.user_id,c.id,'synthetic/legacy','Synthetic legacy blocker','text/plain',1 FROM public.tutor_conversations c JOIN wi24_pairs p ON c.user_id=p.legacy_id;",
                   "DELETE FROM public.tutor_attachments WHERE filename='Synthetic legacy blocker';", "LEGACY_ATTACHMENTS")
        guard_case("role", "UPDATE public.enrollments e SET role='instructor' FROM wi24_pairs p WHERE e.user_id=p.legacy_id;",
                   "UPDATE public.enrollments SET role='student';", "ROLE_COLLISION")
        guard_case("unfinished", "UPDATE public.quiz_set_attempts SET completed_at=NULL;",
                   "UPDATE public.quiz_set_attempts SET completed_at='2020-01-03';", "UNFINISHED_ATTEMPTS")
        guard_case("alias-third-party", "UPDATE public.lms_identity_aliases a SET user_id=q.canonical_id FROM wi24_pairs p,wi24_pairs q "
                   "WHERE p.label=2 AND q.label=1 AND a.lms_user_id='legacy-'||p.label;",
                   "UPDATE public.lms_identity_aliases a SET user_id=p.legacy_id FROM wi24_pairs p WHERE a.lms_user_id='legacy-'||p.label;",
                   "LEGACY_IDENTIFIER_ALIAS_CONFLICT")
        guard_case("stale-mastery", "CREATE TEMP TABLE stale_skill AS WITH inserted AS(INSERT INTO public.skills(institution_id,course_id,name,bloom_level,status) "
                   "SELECT institution_id,course_ids[1],'Synthetic stale','remember','approved' FROM wi24_pairs WHERE label=1 RETURNING *) SELECT * FROM inserted; "
                   "INSERT INTO public.mastery_state(institution_id,user_id,course_id,skill_id,estimate) SELECT s.institution_id,p.canonical_id,s.course_id,s.id,0.7 "
                   "FROM stale_skill s CROSS JOIN wi24_pairs p WHERE p.label=1;",
                   "DELETE FROM public.mastery_state WHERE skill_id IN(SELECT id FROM stale_skill); DELETE FROM public.skills WHERE id IN(SELECT id FROM stale_skill);",
                   "STALE_CANONICAL_MASTERY")
        guard_case("unconstrained-tenant", "INSERT INTO public.item_reviews(institution_id,user_id,course_id,item_id,mode,outcome,was_due,counted,idempotency_key) "
                   "SELECT gen_random_uuid(),p.legacy_id,p.course_ids[1],i.id,'quiz','good',true,false,'synthetic-bad-tenant' "
                   "FROM wi24_pairs p JOIN public.generated_items i ON i.course_id=p.course_ids[1] WHERE p.label=1;",
                   "ALTER TABLE public.item_reviews DISABLE TRIGGER t_immutable; DELETE FROM public.item_reviews WHERE idempotency_key='synthetic-bad-tenant'; "
                   "ALTER TABLE public.item_reviews ENABLE TRIGGER t_immutable;", "TENANT_SCOPE")
        original = repair.snapshot(db)
        assert "CONFIRMED_WORKER_K_REQUIRED" in cli("missing-k",["--apply","--confirm"],expected=2,worker_config=False)
        servicefile.write_text(servicefile.read_text()+f"[remote_stage]\nhost=203.0.113.1\nport=5432\nuser=postgres\ndbname=wi24_bad\n"
                              +f"[option_stage]\nhost=127.0.0.1\nport={port}\nuser=postgres\ndbname=wi24_backup\noptions=-c search_path=public\n")
        assert "LOCAL_SERVICE_REQUIRED" in cli("remote-stage",["--apply","--confirm","--backup-service","remote_stage"],expected=2)
        assert "LOCAL_SERVICE_REQUIRED" in cli("option-stage",["--apply","--confirm","--backup-service","option_stage"],expected=2)
        assert "SEPARATE_LOCAL_BACKUP_REQUIRED" in cli("same-stage",["--apply","--confirm","--backup-service","wi24_source"],expected=2)
        assert repair.snapshot(db)==original
        # Public failure hook is forced to loopback even if hosted release ever changes.
        before_failure=repair.snapshot(db)
        assert "INJECTED_FAILURE" in cli("apply-failure",["--apply","--confirm","--backup-service","wi24_backup","--local-test-failure","after_sources"],expected=2)
        assert repair.snapshot(db)==before_failure
        repair.validate_triggers(db)
        assert db.scalar("SELECT to_jsonb(count(*)) FROM public.audit_log WHERE action='WI24_MERGE';")==0
        local.run("DROP SCHEMA wi24_backup CASCADE;")
        repair.begin(db,apply=True)
        assert "DATABASE_OPERATION_FAILED" in cli("locked-dry",expected=2)
        db.run("ROLLBACK;")
        assert repair.snapshot(db)==before_failure
        text = cli("apply",["--apply","--confirm","--backup-service","wi24_backup"],
                   extra_env={"PGHOSTADDR":"203.0.113.1","PGSERVICE":"untrusted","PGOPTIONS":"bad"})
        assert "applied_pairs=2 timestamp_mismatches=0" in text
        after_apply = repair.snapshot(db)
        assert db.scalar("SELECT to_jsonb(count(*)) FROM public.audit_log WHERE action='WI24_MERGE' AND metadata ? 'backup_sha256';")==2
        for pair in pairs:
            assert resolve(institution_id=inst,lms_user_id=pair["lms_uuid"],role="student",display_name=None,email=None)["id"]==pair["canonical_id"]
            assert resolve(institution_id=inst,lms_user_id="legacy-"+str(pair["label"]),role="student",display_name=None,email=None)["id"]==pair["canonical_id"]
        assert "converged=true source_writes=0" in cli("noop",["--apply","--confirm"])
        assert repair.snapshot(db)==after_apply
        assert db.scalar("SELECT to_jsonb(count(*)) FROM public.audit_log WHERE action='WI24_MERGE';")==2
        assert db.scalar("SELECT to_jsonb(max(attempt_number)) FROM public.quiz_set_attempts;")==2
        assert db.scalar("SELECT to_jsonb(sum(xp_awarded)) FROM public.practice_answer_results;")==36
        assert db.scalar("SELECT to_jsonb(count(*)) FROM public.readiness_snapshots;")==1
        # Exact unchanged job bodies run with only synthetic local SQL adapters.
        reconcile, readiness = worker(ROOT,connection)
        assert reconcile(institution_id=inst)["pairsChecked"]==2
        assert readiness(institution_id=inst)["snapshots"]==2
        assert repair.snapshot(db)!=after_apply
        # Worker changes make an uncaptured restore fail, before any source writes.
        before_refusal = repair.snapshot(db)
        assert "POSTIMAGE_CHANGED" in cli("restore-before-capture",["--apply","--confirm","--restore","--backup-service","wi24_restore"],
                                          expected=2,directory=private/"apply")
        assert repair.snapshot(db)==before_refusal
        # The failed restore's LOCAL staging schema is discarded explicitly.
        restore_db=repair.Psql("wi24_restore",env=env); restore_db.run("DROP SCHEMA wi24_backup CASCADE;"); restore_db.close()
        # Correct counters/timestamps do not bless an incorrect estimate.
        db.run("CREATE TEMP TABLE saved_estimates AS SELECT * FROM public.mastery_state; UPDATE public.mastery_state SET estimate=0.999999;")
        wrong_estimate=repair.snapshot(db)
        assert "MASTERY_ESTIMATE_MISMATCH" in cli("capture-wrong-estimate",["--apply","--confirm","--capture-recompute","--backup-service","wi24_backup"],expected=2,directory=private/"apply")
        assert repair.snapshot(db)==wrong_estimate
        db.run("ALTER TABLE public.mastery_state DISABLE TRIGGER t_updated_at; "
               "UPDATE public.mastery_state m SET estimate=s.estimate,updated_at=s.updated_at FROM saved_estimates s WHERE m.user_id=s.user_id AND m.skill_id=s.skill_id; "
               "ALTER TABLE public.mastery_state ENABLE TRIGGER t_updated_at;")
        # Reject an incomplete replay before creating the recompute archive.
        db.run("CREATE TEMP TABLE saved_mastery AS SELECT * FROM public.mastery_state; "
               "UPDATE public.mastery_state SET attempts=attempts+1;")
        incomplete=repair.snapshot(db)
        assert "INCOMPLETE_MASTERY_REPLAY" in cli("capture-incomplete",["--apply","--confirm","--capture-recompute","--backup-service","wi24_backup"],expected=2,directory=private/"apply")
        assert repair.snapshot(db)==incomplete
        db.run("ALTER TABLE public.mastery_state DISABLE TRIGGER t_updated_at; "
               "UPDATE public.mastery_state m SET attempts=s.attempts,updated_at=s.updated_at FROM saved_mastery s "
               "WHERE m.user_id=s.user_id AND m.skill_id=s.skill_id; ALTER TABLE public.mastery_state ENABLE TRIGGER t_updated_at;")
        assert "recompute_captured=true" in cli("capture",["--apply","--confirm","--capture-recompute","--backup-service","wi24_backup"],directory=private/"apply")
        captured=repair.snapshot(db)
        assert "converged=true source_writes=0" in cli("noop-after-worker",["--apply","--confirm"])
        assert repair.snapshot(db)==captured
        # A later profile write invalidates the entire captured postimage.
        db.run("CREATE TEMP TABLE saved_profiles AS SELECT * FROM public.user_profiles; "
               "UPDATE public.user_profiles t SET display_name='Later synthetic activity' FROM wi24_pairs p WHERE t.user_id=p.canonical_id;")
        later=repair.snapshot(db)
        assert "POSTIMAGE_CHANGED" in cli("restore-later",["--apply","--confirm","--restore","--backup-service","wi24_restore"],expected=2,directory=private/"apply")
        assert repair.snapshot(db)==later
        restore_db=repair.Psql("wi24_restore",env=env); restore_db.run("DROP SCHEMA wi24_backup CASCADE;"); restore_db.close()
        db.run("ALTER TABLE public.user_profiles DISABLE TRIGGER t_updated_at; "
               "UPDATE public.user_profiles t SET display_name=s.display_name,updated_at=s.updated_at FROM saved_profiles s WHERE t.user_id=s.user_id; "
               "ALTER TABLE public.user_profiles ENABLE TRIGGER t_updated_at;")
        assert repair.snapshot(db)==captured
        assert "INJECTED_RESTORE_FAILURE" in cli("restore-failure",["--apply","--confirm","--restore","--backup-service","wi24_restore","--local-test-failure","during_restore"],expected=2,directory=private/"apply")
        assert repair.snapshot(db)==captured
        repair.validate_triggers(db)
        restore_db=repair.Psql("wi24_restore",env=env); restore_db.run("DROP SCHEMA wi24_backup CASCADE; DROP SCHEMA wi24_recompute CASCADE;"); restore_db.close()
        assert "restored_pairs=2 timestamp_mismatches=0" in cli("restore",["--apply","--confirm","--restore","--backup-service","wi24_restore"],directory=private/"apply")
        assert repair.snapshot(db)==original,"exact post-worker restore differs"
        repair.validate_triggers(db)
        assert db.scalar("SELECT to_jsonb(count(*)) FROM public.audit_log WHERE action='WI24_MERGE';")==2
        assert db.scalar("SELECT to_jsonb(count(*)) FROM public.audit_log WHERE action='WI24_ROLLBACK';")==2
        # Exercise canonical-wins and exact-tie SRS branches with actual CLI roundtrips.
        for scenario in ("canonical-wins","canonical-tie"):
            local.run("DROP SCHEMA wi24_backup CASCADE; DROP SCHEMA wi24_recompute CASCADE;")
            stage=repair.Psql("wi24_restore",env=env)
            stage.run("DROP SCHEMA wi24_backup CASCADE;" + (" DROP SCHEMA wi24_recompute CASCADE;" if scenario=="canonical-wins" else ""))
            stage.close()
            db.run("UPDATE public.srs_state s SET last_reviewed_at='2020-04-01' FROM wi24_pairs p "
                   "WHERE p.label=2 AND " + ("s.user_id=p.canonical_id" if scenario=="canonical-wins" else "s.user_id IN(p.canonical_id,p.legacy_id)") + ";")
            branch_preimage=repair.snapshot(db)
            cli(scenario,["--apply","--confirm","--backup-service","wi24_backup"])
            assert db.scalar("SELECT to_jsonb(s.box) FROM public.srs_state s JOIN wi24_pairs p ON p.canonical_id=s.user_id WHERE p.label=2;")==1
            cli(scenario+"-restore",["--apply","--confirm","--restore","--backup-service","wi24_restore"],directory=private/scenario)
            assert repair.snapshot(db)==branch_preimage
            # Only the first loop had a recompute archive/staging schema.
            if scenario=="canonical-wins":
                local.run("CREATE SCHEMA wi24_recompute;")
        # Multiple legacy attempts renumber simultaneously without transient key collisions.
        local.run("DROP SCHEMA wi24_backup CASCADE;")
        stage=repair.Psql("wi24_restore",env=env); stage.run("DROP SCHEMA wi24_backup CASCADE;"); stage.close()
        db.run("CREATE TEMP TABLE extra_attempt AS WITH inserted AS(INSERT INTO public.quiz_set_attempts(institution_id,user_id,course_id,set_id,attempt_number,completed_at) "
               "SELECT a.institution_id,a.user_id,a.course_id,a.set_id,2,'2020-01-04' FROM public.quiz_set_attempts a JOIN wi24_pairs p ON a.user_id=p.legacy_id WHERE p.label=2 RETURNING *) SELECT * FROM inserted; "
               "INSERT INTO public.practice_answer_results(institution_id,user_id,course_id,item_id,set_id,attempt_id,idempotency_key,prompt,choice_id,correct_option_id,correct,xp_awarded,mastery_before_level,mastery_after_level) "
               "SELECT a.institution_id,a.user_id,a.course_id,i.id,a.set_id,a.id,'synthetic-extra-answer','Synthetic','a','a',true,0,'Developing','Developing' FROM extra_attempt a JOIN public.generated_items i ON i.course_id=a.course_id; "
               "UPDATE public.item_exposures t SET times_tested=2 FROM wi24_pairs p WHERE p.label=2 AND t.user_id=p.legacy_id;")
        attempt_preimage=repair.snapshot(db)
        cli("multiple-attempts",["--apply","--confirm","--backup-service","wi24_backup"])
        assert db.scalar("SELECT to_jsonb(max(attempt_number)) FROM public.quiz_set_attempts;")==3
        cli("multiple-attempts-restore",["--apply","--confirm","--restore","--backup-service","wi24_restore"],directory=private/"multiple-attempts")
        assert repair.snapshot(db)==attempt_preimage
        print("PASS canonical/legacy schedule winners and exact ties; multiple attempt renumbering and restore")
        print("PASS public CLI dry-run/apply/no-op/unsafe collision refusal; counts-only stdout")
        print("PASS unchanged resolver function body before/after tombstone and alias transition")
        print("PASS unchanged worker job bodies; exact post-worker derived capture and restore")
        print("PASS uncaptured worker changes refuse restore; source unchanged by refusal")
        print("PASS scoped local pg_dump/pg_restore; collision losers, attempt numbers, derived preimages restored")
        print("PASS public CLI injected apply/restore failure rollback; trigger states restored")
        print("PASS concurrent source access blocked; incomplete worker replay refused")
        print("PASS later activity refuses restore; exact postimage required")
        print("PASS mixed-outcome timestamp ties refused; wrong estimates refused despite correct counters")
        print("PASS profiles/consent/DSR/attachments/roles/aliases/stale mastery and unconstrained tenant guards")
        print("PASS remote/option/same-source staging refused before staging writes")
        print("PASS libpq endpoint override environment discarded; no hosted connection")
    finally:
        if db: db.close()
        if local: local.close()
        if created: docker("rm", "--force", container)
        shutil.rmtree(private)


if __name__ == "__main__":
    run()
