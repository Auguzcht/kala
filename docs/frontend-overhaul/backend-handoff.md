# Backend handoff

Frontend/backend decisions for the question-bank work. Frontend changes keep the agreed API behavior and do not add client-side workarounds.

1. **“All unseen” test size: dropped.** Keep the supported sizes at 5, 10, and 20. Section 7.2 of `docs/design/question-bank-design.md` is updated to match.
2. **Repeat banner on saved sets: dropped.** Saved-set responses do not retain repeat metadata. The frontend does not wait for it or display it on a reopened saved set.
3. **Flashcard deck `bankStatus.usable`:** backend will remove this field. The frontend makes state decisions only from `/courses/{course_id}/bank/status`; no frontend code reads deck `bankStatus.usable`.
4. **Missing bank-state rows:** backend will include every approved skill and use `waiting_content` for skills without a state row. The shared bank schema accepts `waiting_content`; consumers also default a missing entry to that state.
5. **Proposal worker completion signal:** `POST /courses/{course_id}/skills/propose` returns only `{"status":"queued"}` and the worker is invoked asynchronously. There is no persisted proposal run status or read endpoint that reports completion. The instructor UI expects optional `proposalStatus` (`queued`, `running`, `done`, `failed`) on `GET /dashboard/{course_id}/skills/proposed`; backend must persist and return this signal for polling to stop and the finished state to appear reliably.
