"""Valid admission rows for retained business tests, not authorization tests.

Only the Bank guard's exact course/enrollment projections are supplied here.
Other queries and business assertions still use each test's original fixture.
The dedicated AUTH-REQ-007 matrix exercises admission without this adapter.
"""


def enrolled_student_reads(select):
    def scoped(table, params, **kwargs):
        if table == "courses" and params.get("select") == "id,institution_id,bank_serving":
            return [{"id": params["id"][3:], "institution_id": params["institution_id"][3:],
                     "bank_serving": False}]
        if table == "enrollments" and set(params) == {"course_id", "user_id", "select", "limit"} and params.get("select") == "user_id" and params.get("limit") == "1":
            return [{"user_id": params["user_id"][3:]}]
        return select(table, params, **kwargs)
    return scoped
