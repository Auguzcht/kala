# TOUR-REFRESH static audit

Base: `3a6a0aab27a8212f77b83e96b26127d830a696ba`. Audited before implementation. Existence means a source anchor, not unconditional rendering. Every conditional anchor requires a runtime skip.

## Student saved

| Step | Route | Target | Exists in base? | Copy/current-state finding |
| --- | --- | --- | --- | --- |
| 1 | `/course/diagnostic` | `#tour-diagnostic-card` | Yes, conditional | Answering only; completed/caught-up screen absent. Submit is observational; no modal. Header/results not covered. |
| 2 | `/course/diagnostic` | `#tour-diagnostic-choices` | Yes, conditional | Answering only; completed/caught-up screen absent. Submit is observational; no modal. Header/results not covered. |
| 3 | `/course/diagnostic` | `#tour-diagnostic-submit` | Yes, conditional | Answering only; completed/caught-up screen absent. Submit is observational; no modal. Header/results not covered. |
| 4 | `/course/skill/prepared` | `#tour-lesson-explain` | Yes, conditional | Current; conditional target must skip when absent. |
| 5 | `/course/skill/prepared` | `#tour-lesson-dock-toggle` | Generated dock anchor / inspect runtime | Current; conditional target must skip when absent. |
| 6 | `/course/skill/prepared` | `#tour-lesson-dock-input` | Generated dock anchor / inspect runtime | Current; conditional target must skip when absent. |
| 7 | `/course/skill/prepared` | `#tour-lesson-dock-toggle` | Generated dock anchor / inspect runtime | Current; conditional target must skip when absent. |
| 8 | `/course/skill/prepared` | `#tour-lesson-continue` | Yes, conditional | Current; conditional target must skip when absent. |
| 9 | `/course/skill/prepared` | `#tour-lesson-check, #tour-lesson-explain` | Yes, conditional | Current; conditional target must skip when absent. |
| 10 | `/course/skill/prepared` | `#tour-lesson-check-feedback, #tour-lesson-explain` | Yes, conditional | Current; conditional target must skip when absent. |
| 11 | `/course/skill/prepared` | `#tour-study-actions` | Yes, conditional | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 12 | `/course/skill/prepared` | `#tour-study-dock` | Yes, conditional | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 13 | `/course/skill/prepared` | `#tour-study-dock-toggle` | Generated dock anchor / inspect runtime | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 14 | `/course/skill/prepared` | `#tour-study-dock-input` | Generated dock anchor / inspect runtime | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 15 | `/course/skill/prepared` | `#tour-study-dock-toggle` | Generated dock anchor / inspect runtime | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 16 | `/course/skill/prepared` | `#tour-study-dock` | Yes, conditional | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 17 | `/course/skill/prepared` | `#tour-test-start` | Yes, conditional | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 18 | `/course/skill/prepared` | `#tour-practice-choices` | Yes, conditional | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 19 | `/course/skill/prepared` | `#tour-practice-feedback` | Yes, conditional | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 20 | `/course/skill/prepared` | `#tour-test-dock-toggle` | Generated dock anchor / inspect runtime | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 21 | `/course/skill/prepared` | `#tour-test-dock-input` | Generated dock anchor / inspect runtime | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 22 | `/course/skill/prepared` | `#tour-test-dock-toggle` | Generated dock anchor / inspect runtime | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 23 | `/course/tutor` | `#tour-tutor-input` | Yes, conditional | Draft-only sample current; missing history groups/rename-pin, new chat, attach/filedrop and thinking explanation. |
| 24 | `/course/tutor` | `#tour-tutor-response, #tour-tutor-input` | Yes, conditional | Draft-only sample current; missing history groups/rename-pin, new chat, attach/filedrop and thinking explanation. |
| 25 | `/course/twin` | `#tour-twin-readiness` | Yes, conditional | Instrument exists; activity copy overstates live updates; recent evidence ledger missing. |
| 26 | `/course/twin` | `#tour-twin-radar` | Yes, conditional | Instrument exists; activity copy overstates live updates; recent evidence ledger missing. |
| 27 | `/course/twin` | `#tour-twin-activity` | Yes, conditional | Instrument exists; activity copy overstates live updates; recent evidence ledger missing. |
## Student without saved set

| Step | Route | Target | Exists in base? | Copy/current-state finding |
| --- | --- | --- | --- | --- |
| 1 | `/course/diagnostic` | `#tour-diagnostic-card` | Yes, conditional | Answering only; completed/caught-up screen absent. Submit is observational; no modal. Header/results not covered. |
| 2 | `/course/diagnostic` | `#tour-diagnostic-choices` | Yes, conditional | Answering only; completed/caught-up screen absent. Submit is observational; no modal. Header/results not covered. |
| 3 | `/course/diagnostic` | `#tour-diagnostic-submit` | Yes, conditional | Answering only; completed/caught-up screen absent. Submit is observational; no modal. Header/results not covered. |
| 4 | `/course/skill/prepared` | `#tour-lesson-explain` | Yes, conditional | Current; conditional target must skip when absent. |
| 5 | `/course/skill/prepared` | `#tour-lesson-dock-toggle` | Generated dock anchor / inspect runtime | Current; conditional target must skip when absent. |
| 6 | `/course/skill/prepared` | `#tour-lesson-dock-input` | Generated dock anchor / inspect runtime | Current; conditional target must skip when absent. |
| 7 | `/course/skill/prepared` | `#tour-lesson-dock-toggle` | Generated dock anchor / inspect runtime | Current; conditional target must skip when absent. |
| 8 | `/course/skill/prepared` | `#tour-lesson-continue` | Yes, conditional | Current; conditional target must skip when absent. |
| 9 | `/course/skill/prepared` | `#tour-lesson-check, #tour-lesson-explain` | Yes, conditional | Current; conditional target must skip when absent. |
| 10 | `/course/skill/prepared` | `#tour-lesson-check-feedback, #tour-lesson-explain` | Yes, conditional | Current; conditional target must skip when absent. |
| 11 | `/course/skill/prepared` | `#tour-study-actions` | Yes, conditional | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 12 | `/course/skill/prepared` | `#tour-study-dock` | Yes, conditional | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 13 | `/course/skill/prepared` | `#tour-study-dock-toggle` | Generated dock anchor / inspect runtime | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 14 | `/course/skill/prepared` | `#tour-study-dock-input` | Generated dock anchor / inspect runtime | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 15 | `/course/skill/prepared` | `#tour-study-dock-toggle` | Generated dock anchor / inspect runtime | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 16 | `/course/skill/prepared` | `#tour-study-dock` | Yes, conditional | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 17 | `/course/skill/prepared` | `#tour-test-new-set` | Yes, conditional | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 18 | `/course/skill/prepared` | `#tour-test-start` | Yes, conditional | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 19 | `/course/skill/prepared` | `#tour-practice-choices` | Yes, conditional | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 20 | `/course/skill/prepared` | `#tour-practice-feedback` | Yes, conditional | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 21 | `/course/skill/prepared` | `#tour-test-dock-toggle` | Generated dock anchor / inspect runtime | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 22 | `/course/skill/prepared` | `#tour-test-dock-input` | Generated dock anchor / inspect runtime | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 23 | `/course/skill/prepared` | `#tour-test-dock-toggle` | Generated dock anchor / inspect runtime | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 24 | `/course/tutor` | `#tour-tutor-input` | Yes, conditional | Draft-only sample current; missing history groups/rename-pin, new chat, attach/filedrop and thinking explanation. |
| 25 | `/course/tutor` | `#tour-tutor-response, #tour-tutor-input` | Yes, conditional | Draft-only sample current; missing history groups/rename-pin, new chat, attach/filedrop and thinking explanation. |
| 26 | `/course/twin` | `#tour-twin-readiness` | Yes, conditional | Instrument exists; activity copy overstates live updates; recent evidence ledger missing. |
| 27 | `/course/twin` | `#tour-twin-radar` | Yes, conditional | Instrument exists; activity copy overstates live updates; recent evidence ledger missing. |
| 28 | `/course/twin` | `#tour-twin-activity` | Yes, conditional | Instrument exists; activity copy overstates live updates; recent evidence ledger missing. |
## Student completed sets

| Step | Route | Target | Exists in base? | Copy/current-state finding |
| --- | --- | --- | --- | --- |
| 1 | `/course/diagnostic` | `#tour-diagnostic-card` | Yes, conditional | Answering only; completed/caught-up screen absent. Submit is observational; no modal. Header/results not covered. |
| 2 | `/course/diagnostic` | `#tour-diagnostic-choices` | Yes, conditional | Answering only; completed/caught-up screen absent. Submit is observational; no modal. Header/results not covered. |
| 3 | `/course/diagnostic` | `#tour-diagnostic-submit` | Yes, conditional | Answering only; completed/caught-up screen absent. Submit is observational; no modal. Header/results not covered. |
| 4 | `/course/skill/prepared` | `#tour-lesson-explain` | Yes, conditional | Current; conditional target must skip when absent. |
| 5 | `/course/skill/prepared` | `#tour-lesson-dock-toggle` | Generated dock anchor / inspect runtime | Current; conditional target must skip when absent. |
| 6 | `/course/skill/prepared` | `#tour-lesson-dock-input` | Generated dock anchor / inspect runtime | Current; conditional target must skip when absent. |
| 7 | `/course/skill/prepared` | `#tour-lesson-dock-toggle` | Generated dock anchor / inspect runtime | Current; conditional target must skip when absent. |
| 8 | `/course/skill/prepared` | `#tour-lesson-continue` | Yes, conditional | Current; conditional target must skip when absent. |
| 9 | `/course/skill/prepared` | `#tour-lesson-check, #tour-lesson-explain` | Yes, conditional | Current; conditional target must skip when absent. |
| 10 | `/course/skill/prepared` | `#tour-lesson-check-feedback, #tour-lesson-explain` | Yes, conditional | Current; conditional target must skip when absent. |
| 11 | `/course/skill/prepared` | `#tour-study-actions` | Yes, conditional | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 12 | `/course/skill/prepared` | `#tour-study-dock` | Yes, conditional | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 13 | `/course/skill/prepared` | `#tour-study-dock-toggle` | Generated dock anchor / inspect runtime | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 14 | `/course/skill/prepared` | `#tour-study-dock-input` | Generated dock anchor / inspect runtime | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 15 | `/course/skill/prepared` | `#tour-study-dock-toggle` | Generated dock anchor / inspect runtime | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 16 | `/course/skill/prepared` | `#tour-study-dock` | Yes, conditional | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 17 | `/course/skill/prepared` | `#tour-test-menu` | Yes, conditional | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 18 | `/course/skill/prepared` | `#tour-test-new-set` | Yes, conditional | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 19 | `/course/tutor` | `#tour-tutor-input` | Yes, conditional | Draft-only sample current; missing history groups/rename-pin, new chat, attach/filedrop and thinking explanation. |
| 20 | `/course/tutor` | `#tour-tutor-response, #tour-tutor-input` | Yes, conditional | Draft-only sample current; missing history groups/rename-pin, new chat, attach/filedrop and thinking explanation. |
| 21 | `/course/twin` | `#tour-twin-readiness` | Yes, conditional | Instrument exists; activity copy overstates live updates; recent evidence ledger missing. |
| 22 | `/course/twin` | `#tour-twin-radar` | Yes, conditional | Instrument exists; activity copy overstates live updates; recent evidence ledger missing. |
| 23 | `/course/twin` | `#tour-twin-activity` | Yes, conditional | Instrument exists; activity copy overstates live updates; recent evidence ledger missing. |
## Instructor

| Step | Route | Target | Exists in base? | Copy/current-state finding |
| --- | --- | --- | --- | --- |
| 1 | `/class` | `#tour-cohort-kpis` | Yes, conditional | Current; conditional target must skip when absent. |
| 2 | `/class` | `#roster-panel` | Yes, conditional | Current; conditional target must skip when absent. |
| 3 | `/class` | `#tour-roster-search` | Yes, conditional | Current; conditional target must skip when absent. |
| 4 | `/class` | `#tour-roster-filter` | Yes, conditional | Current; conditional target must skip when absent. |
| 5 | `/class` | `#tour-roster-first-row` | Yes, conditional | Current; conditional target must skip when absent. |
| 6 | `/class` | `#tour-standing` | Yes, conditional | Current; conditional target must skip when absent. |
| 7 | `/class` | `#tour-decide-center` | Yes, conditional | Current; conditional target must skip when absent. |
| 8 | `/class` | `#tour-standing` | Yes, conditional | Current; conditional target must skip when absent. |
| 9 | `/class` | `#at-risk-list` | Yes, conditional | Current; conditional target must skip when absent. |
| 10 | `/class` | `#cohort-analytics` | Generated dock anchor / inspect runtime | Current; conditional target must skip when absent. |
| 11 | `/class` | `#tour-tab-heatmap` | Yes, conditional | Current; conditional target must skip when absent. |
| 12 | `/class` | `#heatmap-panel` | Generated dock anchor / inspect runtime | Current; conditional target must skip when absent. |
| 13 | `/class` | `#tour-skill-review-trigger` | Yes, conditional | Current; conditional target must skip when absent. |
| 14 | `/class` | `#tour-skill-review-panel` | Yes, conditional | Current; conditional target must skip when absent. |
| 15 | `/class` | `#tour-skill-approve` | Yes, conditional | Current; conditional target must skip when absent. |
| 16 | `/class` | `#tour-at-risk-first-flag` | Yes, conditional | Current; conditional target must skip when absent. |
| 17 | `/class/student/$uid` | `#tour-standing` | Yes, conditional | Current; conditional target must skip when absent. Runner route matcher currently compares literal $uid and cannot resume. |
| 18 | `/class/student/$uid` | `#tour-tab-decide` | Yes, conditional | Current; conditional target must skip when absent. Runner route matcher currently compares literal $uid and cannot resume. |
| 19 | `/class/student/$uid` | `#tour-decide-center` | Yes, conditional | Current; conditional target must skip when absent. Runner route matcher currently compares literal $uid and cannot resume. |
| 20 | `/class/student/$uid` | `#tour-run-analysis` | Yes, conditional | Current; conditional target must skip when absent. Runner route matcher currently compares literal $uid and cannot resume. |
| 21 | `/class/student/$uid` | `#tour-rec-card` | Yes, conditional | Current; conditional target must skip when absent. Runner route matcher currently compares literal $uid and cannot resume. |
| 22 | `/class/student/$uid` | `#tour-decision-buttons` | Yes, conditional | Current; conditional target must skip when absent. Runner route matcher currently compares literal $uid and cannot resume. |
| 23 | `/class/student/$uid` | `#tour-tab-mastery` | Yes, conditional | Current; conditional target must skip when absent. Runner route matcher currently compares literal $uid and cannot resume. |
| 24 | `/class/student/$uid` | `#tour-record-radar` | Yes, conditional | Current; conditional target must skip when absent. Runner route matcher currently compares literal $uid and cannot resume. |
| 25 | `/class/student/$uid` | `#tour-record-intervene` | Yes, conditional | Current; conditional target must skip when absent. Runner route matcher currently compares literal $uid and cannot resume. |
| 26 | `/class/student/$uid` | `#tour-tab-activity` | Yes, conditional | Current; conditional target must skip when absent. Runner route matcher currently compares literal $uid and cannot resume. |
| 27 | `/class/student/$uid` | `#tour-record-ledger` | Yes, conditional | Current; conditional target must skip when absent. Runner route matcher currently compares literal $uid and cannot resume. |

## Coverage decisions

No starter-suggestion, sidebar-collapse or Diagnostic-modal step exists in this base; none will be introduced. Tutor thinking is transient and described with the response area rather than waiting for a model request. Attach and conversation management are highlights only. Study end controls and Test/Diagnostic results are optional highlights and never reached by automatic answers, ratings or submission. The tour keeps navigation/UI toggles only. No hosted state or provider claims.
