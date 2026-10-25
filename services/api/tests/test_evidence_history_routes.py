"""WI-25 / TWIN-REQ-010 / INSTR-REQ-010: real SEC guards, synthetic DB boundary."""
from datetime import datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.deps import CurrentUser, get_current_user
from app.main import app
from app.twin import evidence_history

I, J, COURSE, OTHER_COURSE, FOREIGN_COURSE, STUDENT, OTHER_STUDENT, TEACHER, OTHER_TEACHER, FOREIGN_TEACHER, ADMIN = [str(UUID(int=n)) for n in range(1, 12)]


@pytest.fixture
def system(monkeypatch):
    state = {"actor": CurrentUser(STUDENT, I, "student"), "reads": [], "writes": []}
    memberships = [
        dict(institution_id=I, user_id=STUDENT, course_id=COURSE, role="student"),
        dict(institution_id=I, user_id=OTHER_STUDENT, course_id=OTHER_COURSE, role="student"),
        dict(institution_id=I, user_id=TEACHER, course_id=COURSE, role="instructor"),
        dict(institution_id=I, user_id=OTHER_TEACHER, course_id=OTHER_COURSE, role="instructor"),
        # Even a malformed cross-institution enrollment cannot bypass _course_ref.
        dict(institution_id=J, user_id=FOREIGN_TEACHER, course_id=COURSE, role="instructor"),
    ]
    courses = [dict(id=COURSE,institution_id=I,lms_course_id="synthetic"),
               dict(id=OTHER_COURSE,institution_id=I,lms_course_id="synthetic-other"),
               dict(id=FOREIGN_COURSE,institution_id=J,lms_course_id="synthetic-foreign")]
    users = [dict(id=STUDENT,institution_id=I,role="student"),
             dict(id=OTHER_STUDENT,institution_id=I,role="student")]
    events = [{"id":str(UUID(int=n)),"institution_id":I,"user_id":STUDENT,"course_id":COURSE,
               "skill_id":None,"created_at":"2026-10-25T12:00:00+00:00", "type":"practice","correct":True}
              for n in range(100,161)]
    events.sort(key=lambda e:e["id"],reverse=True)
    state["events"] = events
    state["memberships"] = memberships
    def select(table, params):
        state["reads"].append((table,params.copy()))
        source = {"courses":courses,"enrollments":memberships,"users":users,"evidence_events":events}[table]
        rows = source[:]
        for key,value in params.items():
            if value.startswith("eq.") and key not in {"select","order"}:
                rows = [r for r in rows if r.get(key)==value[3:]]
            elif value.startswith("in.("):
                rows = [r for r in rows if r.get(key) in value[4:-1].split(",")]
        if "or" in params:
            timestamp = params["or"].split("created_at.lt.")[1].split(",and(")[0]
            event_id = params["or"].split("id.lt.")[1].split(")")[0]
            rows = [r for r in rows if (datetime.fromisoformat(r["created_at"]),r["id"]) <
                    (datetime.fromisoformat(timestamp),event_id)]
        return rows[:int(params.get("limit",len(rows)))]
    monkeypatch.setattr(evidence_history.db,"select",select)
    def no_write(*args,**kwargs):
        state["writes"].append(True)
        raise AssertionError("history views must not write or call RPC")
    for method in ("insert","upsert","update","delete","rpc"):
        monkeypatch.setattr(evidence_history.db,method,no_write)
    app.dependency_overrides[get_current_user] = lambda:state["actor"]
    with TestClient(app) as client:
        yield client,state
    app.dependency_overrides.clear()


def own(course=COURSE): return f"/courses/{course}/twin/evidence"
def staff(course=COURSE, learner=STUDENT): return f"/dashboard/{course}/students/{learner}/evidence"


@pytest.mark.parametrize("route",[own(),staff()])
def test_wi25_route_first_next_last_and_ties(system,route):
    client,state=system
    if route.startswith("/dashboard"):state["actor"]=CurrentUser(TEACHER,I,"instructor")
    pages=[];cursor=None
    for _ in range(3):
        r=client.get(route,params={} if cursor is None else {"cursor":cursor})
        assert r.status_code==200
        pages.append(r.json());cursor=r.json()["nextCursor"]
    assert [len(p["evidence"]) for p in pages]==[25,25,11]
    assert cursor is None
    assert [e["id"] for p in pages for e in p["evidence"]]==[e["id"] for e in state["events"]]
    assert not state["writes"]


@pytest.mark.parametrize("actor,course,target,status",[
    (CurrentUser(STUDENT,I,"student"),COURSE,STUDENT,403),
    (CurrentUser(OTHER_TEACHER,I,"instructor"),COURSE,STUDENT,404),
    (CurrentUser(FOREIGN_TEACHER,J,"instructor"),COURSE,STUDENT,404),
    (CurrentUser(ADMIN,J,"admin"),COURSE,STUDENT,404),
    (CurrentUser(TEACHER,I,"instructor"),COURSE,OTHER_STUDENT,404),
    (CurrentUser(TEACHER,I,"instructor"),FOREIGN_COURSE,STUDENT,404),
    (CurrentUser(TEACHER,I,"instructor"),COURSE,STUDENT,200),
    (CurrentUser(ADMIN,I,"admin"),COURSE,STUDENT,200),
])
def test_wi25_staff_actor_matrix(system,actor,course,target,status):
    client,state=system;state["actor"]=actor
    r=client.get(staff(course,target))
    assert r.status_code==status
    if status!=200:assert not any(t=="evidence_events" for t,_ in state["reads"])
    assert not state["writes"]


@pytest.mark.parametrize("actor,course,status",[
    (CurrentUser(STUDENT,I,"student"),COURSE,200),
    (CurrentUser(STUDENT,I,"student"),OTHER_COURSE,404),
    (CurrentUser(STUDENT,I,"student"),FOREIGN_COURSE,404),
    (CurrentUser(STUDENT,J,"student"),COURSE,404),
    (CurrentUser(TEACHER,I,"instructor"),COURSE,403),
    (CurrentUser(ADMIN,I,"admin"),COURSE,403),
])
def test_wi25_own_actor_matrix(system,actor,course,status):
    client,state=system;state["actor"]=actor
    r=client.get(own(course))
    assert r.status_code==status
    if status!=200:assert not any(t=="evidence_events" for t,_ in state["reads"])
    assert not state["writes"]


@pytest.mark.parametrize("route",[own(),staff()])
@pytest.mark.parametrize("limit,status",[(0,422),(-1,422),(101,422),("bad",422),(1,200),(100,200)])
def test_wi25_route_limit_bounds(system,route,limit,status):
    client,state=system
    if route.startswith("/dashboard"):state["actor"]=CurrentUser(TEACHER,I,"instructor")
    r=client.get(route,params={"limit":limit})
    assert r.status_code==status
    if status==422:assert not any(t=="evidence_events" for t,_ in state["reads"])


@pytest.mark.parametrize("route",[own(),staff()])
@pytest.mark.parametrize("cursor",["","bad","a.b","x"*2049])
def test_wi25_route_bad_cursor(system,route,cursor):
    client,state=system
    if route.startswith("/dashboard"):state["actor"]=CurrentUser(TEACHER,I,"instructor")
    r=client.get(route,params={"cursor":cursor})
    assert r.status_code==422
    assert r.json()=={"detail":"invalid evidence cursor"}
    assert not any(t=="evidence_events" for t,_ in state["reads"])


def test_wi25_rechecks_admission_on_every_cursor_page(system):
    client,state=system;state["actor"]=CurrentUser(TEACHER,I,"instructor")
    cursor=client.get(staff(),params={"limit":1}).json()["nextCursor"]
    state["memberships"][:]=[m for m in state["memberships"] if m["user_id"]!=TEACHER]
    state["reads"].clear()
    assert client.get(staff(),params={"cursor":cursor}).status_code==404
    assert not any(t=="evidence_events" for t,_ in state["reads"])


def test_wi25_signed_cursor_cannot_cross_callers(system):
    client,state=system
    cursor=client.get(own(),params={"limit":1}).json()["nextCursor"]
    state["actor"]=CurrentUser(TEACHER,I,"instructor");state["reads"].clear()
    assert client.get(staff(),params={"cursor":cursor}).status_code==422
    assert not any(t=="evidence_events" for t,_ in state["reads"])


def test_wi25_own_query_cannot_override_identity(system):
    client,state=system
    assert client.get(own(),params={"user_id":OTHER_STUDENT}).status_code==200
    params=next(p for t,p in state["reads"] if t=="evidence_events")
    assert params["user_id"]==f"eq.{STUDENT}"


def test_wi25_empty_history_serializes_final_cursor(system):
    client,state=system;state["events"].clear()
    assert client.get(own()).json()=={"courseId":COURSE,"evidence":[],"nextCursor":None}


@pytest.mark.parametrize("role,expected",[
    ("instructor",["enrollments","courses","enrollments","users","evidence_events"]),
    ("admin",["courses","enrollments","users","evidence_events"]),
])
def test_wi25_staff_guard_order(system,role,expected):
    client,state=system;state["actor"]=CurrentUser(TEACHER if role=="instructor" else ADMIN,I,role)
    assert client.get(staff()).status_code==200
    assert [t for t,_ in state["reads"]]==expected


@pytest.mark.parametrize("route",[own(),staff()])
def test_wi25_requires_authenticated_session(system,route):
    client,state=system;app.dependency_overrides.clear()
    assert client.get(route).status_code==401
    assert not state["reads"] and not state["writes"]


def test_wi25_route_tamper_and_cross_course_cursor(system):
    client,state=system;state["actor"]=CurrentUser(TEACHER,I,"instructor")
    cursor=client.get(staff(),params={"limit":1}).json()["nextCursor"]
    state["memberships"].extend([
        dict(institution_id=I,user_id=TEACHER,course_id=OTHER_COURSE,role="instructor"),
        dict(institution_id=I,user_id=STUDENT,course_id=OTHER_COURSE,role="student"),
    ])
    state["reads"].clear()
    assert client.get(staff(OTHER_COURSE),params={"cursor":cursor}).status_code==422
    assert not any(t=="evidence_events" for t,_ in state["reads"])
    changed=("A" if cursor[0]!="A" else "B")+cursor[1:]
    assert client.get(staff(),params={"cursor":changed}).status_code==422
    assert not any(t=="evidence_events" for t,_ in state["reads"])
