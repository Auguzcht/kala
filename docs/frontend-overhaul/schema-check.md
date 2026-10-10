# Practice, flashcard, and bank status schema check

Compared the current API router return values against the frontend Zod schemas. Zod strips unknown response fields so additive backend fields do not break clients. In development, unknown fields are logged with the endpoint. Missing required fields and wrong-typed fields still throw, with the Zod error logged in development. Status values for `skill_bank_state` come from migration 0021: `waiting_content`, `building`, `ready`, `no_material`, and `error`.

## Practice router

Router: `services/api/app/routers/practice.py`.

| Response / router field | Zod field | Match | Notes |
|---|---|---:|---|
| `GET /{course}/next`: `courseId` | `practiceNext.courseId` | Yes | |
| `GET /{course}/next`: `item` (`id`, `skillId`, nullable `bloomLevel`, `prompt`, `choices[]`) | `practiceNext.item` / `practiceItem` | Yes | Bank and legacy response item shapes align. |
| `GET /{course}/next`: optional `bankStatus` (`status`, `mcqReady`, `mcqTarget`, `usable`) | `practiceNext.bankStatus` | Yes | Status is now an enum. |
| `POST /{course}/set`: `courseId`, nullable `setId`, `items[]` | `practiceSet` | Yes | |
| `POST /{course}/set`: `skillId` | optional nullable `skillId` | Yes | Absent only when there is no resolved skill. |
| `POST /{course}/set`: `kind: "practice"` | optional `kind` | Yes | Omitted by the no-approved-skill short response. |
| `POST /{course}/set`: `status` | `generating | ready | failed | preparing | no_material` | Yes | These are set response states, distinct from bank skill states. |
| `POST /{course}/set`: `requestedSize`, `readyCount`, `pendingCount`, `failedCount`, `failedOffsets` | same names | Yes | |
| `POST /{course}/set`: optional `bankStatus` (`status`, ready/target counts, `usable`) | `practiceSet.bankStatus` | Yes | Uses the shared bank status enum. |
| `POST /{course}/set`: optional `includesRepeats` | `practiceSet.includesRepeats` | Yes | Bank ready response only. |
| `POST /{course}/set`: `items[]` | `practiceSet.items` | Yes | |
| `POST /{course}/set/from-items`: `courseId`, `setId`, `items[]` | `practiceBridgeSet` | Yes | No skill or set status is returned. |
| `GET /{course}/sets`: `courseId`, `sets[]` | `practiceSetList` | Yes | |
| Set summary: `setId`, `skillId`, `kind`, `size`, `createdAt` | `practiceSetSummary` | Yes | |
| Set summary: `attemptedCount`, `correctCount`, `lastAttemptedAt` (nullable) | `practiceSetAttempt` | Yes | |
| `GET /{course}/sets/{set}`: `_practice_set_view` fields plus attempt fields | `practiceSavedSet` | Yes | `includesRepeats` is not returned for saved sets; see backend handoff. |
| `POST /{course}/submit`: `correct`, `explanation`, nullable `mastery` | `practiceSubmitResult` | Yes | |

All object schemas for these responses are strict. The client no longer silently strips unmodeled response keys.

## Flashcards router

Router: `services/api/app/routers/flashcards.py`.

| Response / router field | Zod field | Match | Notes |
|---|---|---:|---|
| `GET /{course}/deck`: `courseId`, `cards[]`, `stats` | `flashcardDeck` | Yes | |
| Card: `itemId`, `skillId`, nullable `skillName`, `prompt`, `state`, `box`, `back` | `flashcardCard` | Yes | `skillName` may be null or omitted. |
| Card `state`: `due` or `new` | enum | Yes | |
| Card `back`: nullable `label`, `explanation` | `flashcardBack` | Yes | |
| Stats: `tracked`, `due`, `learning`, `mastered` | `srsStats` | Yes | |
| Optional deck `bankStatus`: `status`, `mcqReady` | `flashcardDeck.bankStatus` | Yes | `usable` is being removed by the backend; frontend state uses the shared bank status endpoint. |
| `POST /{course}/review`: `remembered`, `graduated`, `dueInHours`, `box`, `reward` | `flashcardReviewResult` | Yes | |
| Reward: `xp`, `attempts`, `correct`, `streakDays`, `badges[]` | `rewardSchema` | Yes | |
| Badge: `kind`, `label`, `tier` | badge object | Yes | |

All response objects are strict, including nested cards, stats, review rewards, and badges.

## Bank status router

Router: `services/api/app/routers/bank.py`; allowed status values are constrained in `packages/db/migrations/0021_question_bank.sql`.

| Response / router field | Zod field | Match | Notes |
|---|---|---:|---|
| `courseId` | `bankStatus.courseId` | Yes | |
| top-level `building` | `bankStatus.building` | Yes | Shared hook polls at 10 seconds only while this is true. |
| `skills[]`: `skillId`, `status`, `mcqReady`, `mcqTarget`, `depth`, `usable` | `bankSkillStatusEntry` | Yes | `usable` comes from the API; it is never computed in the client. Missing rows are represented by the backend as `waiting_content`. |
| Instructor/admin-only `lastError` | optional nullable `lastError` | Yes | Student endpoint omits it. |
| `bankServing` | `bankStatus.bankServing` | Yes | |

## Backend handoff items

See `docs/frontend-overhaul/backend-handoff.md` for the decisions and the remaining proposal worker completion contract.
