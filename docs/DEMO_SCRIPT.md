# Cintana video: demo script and the decisions behind it

Working doc for the final recording. Written against what the prototype
actually does after the polish pass, not against the mockup.

---

## 1. The through-line

Your professor's note is right and it is the single most important
constraint on this video: **one learner, one teacher, one continuous
journey.** Not a feature tour.

The sentence the whole video has to earn:

> Kala does not replace the teacher. It gives the teacher an intelligent
> view of the learner's current state, predicts what the learner needs
> next, and lets the teacher decide which AI recommendations guide the
> learner.

Everything below is arranged so that each beat makes the next one
inevitable.

---

## 2. What changed in the product, and why it matters to the story

The old build could not tell this story, for three concrete reasons.

**The teacher had no teacher view.** Clicking a student on the instructor
dashboard rendered `TwinBody` — the student's own twin component — with the
streak tile hidden. The teacher was literally looking at the student app.
There was no teacher-shaped question being answered, so there was nothing
to narrate.

Now there is `LearnerRecord`, which leads with the two things a teacher can
only learn by comparison: **standing against the cohort** (percentile, and
the point gap versus the class average) and **momentum** (last ten graded
attempts against the previous ten). A learner at 45% climbing needs a
different conversation than a learner at 45% sliding, and a static mastery
number hides that completely.

**The roster showed `anon-8f2c1b`.** `user_profiles.display_name` existed in
the schema and was never read. It is very hard to build an emotional story
around a class list of hashes. It also showed non-students, because the
cohort query filtered on `enrollments.role` only, so a co-teacher with a
mis-mapped LTI role claim appeared as a learner at 0% mastery.

**The human-in-the-loop claim had no data model.** `recommendations` was
created in migration 0001 and nothing ever wrote to it. The approve/reject
flow in the mockup was a picture of a thing that did not exist. It exists
now: migration 0009 gives it status, priority, evidence, confidence,
decided_by, decided_at, decision_note, instructor_note.

That last point is the one that makes or breaks the video. If a judge asks
"is the approve button real", the answer is now yes, and you can prove it
by showing the item appear on the student's screen.

---

## 3. Recording setup

Do this before you hit record.

- **Seed one learner properly.** Pick your protagonist (Alfred). He needs:
  a diagnostic completed, several practice sessions across at least four
  skills, one clearly weak skill, one clearly strong skill, and at least
  two days of readiness snapshots so the trend line draws. A flat or empty
  trend chart on camera is worse than no chart.
- **Seed one contrast learner.** Someone flagged needs-support with a real
  inactivity gap, so the roster shows triage working rather than a wall of
  identical rows.
- **Run the analysis once beforehand and decline one recommendation.** Then
  re-run it live. This means the Decision history section has content when
  you open it, which is the proof that decisions persist.
- **Two browser profiles, side by side.** Hanna's instructor session and
  Alfred's student session. The final beat needs both on screen.
- **Leave the de-identify switch OFF to start.** You will turn it on
  deliberately, on camera. That is the ethics beat.
- **Check the model path.** If Bedrock is reachable, recommendations come
  from the model. If not, `prescriber.py` falls back to arithmetic and the
  cards say so. Either is honest and either records fine, but know which
  one you are getting so your narration matches the `source` line at the
  bottom of the card.

---

## 4. The script

Total 4:15. Timings are targets, not straitjackets.

### 0:00 – 0:20 · Hook: the problem

**Visual:** Canvas/Blackboard gradebook for AWS101. Scroll it. A wall of
numbers.

**Narration:**
> This is a real course gradebook. Every one of these numbers is true, and
> none of them tell a teacher what to do on Monday. The LMS records that a
> learner scored 58%. It cannot tell you which of the six things behind that
> 58% they actually failed to understand.

Cut to the Kala class overview.

> Kala is the layer that answers that.

### 0:20 – 0:40 · Team and title

**Visual:** Title card. Team names.

Keep it short. Nobody's rubric rewards a long title card, and you need the
seconds later.

### 0:40 – 1:10 · The challenge, through one learner

**Visual:** The class overview, KPI strip visible. Then the roster.

**Narration:**
> Hanna teaches twenty-four students in AWS101. Her problem is not a lack of
> data. It is that the data is scattered across quizzes, submissions, and
> discussion posts, and none of it is organised around the question she
> actually has: who needs me today?

Point at the KPI strip.

> Kala answers that first. Twenty-four learners, eighteen active this week,
> cohort readiness at sixty-three percent, and five recommendations waiting
> on her decision.

Scroll to the roster. Sort by status is the default.

> The roster is sorted by who needs her first, not alphabetically.

### 1:10 – 1:40 · The innovation

**Visual:** Slide or simple animation: LMS → Kala → digital twin → AI
analysis → teacher decision → learner.

**Narration:**
> Kala reads the LMS through LTI. It does not host courses and it does not
> replace anything. It turns scattered evidence into a longitudinal model of
> each learner — a digital twin — mapped to Bloom's taxonomy. The AI reads
> that twin, and proposes. The teacher decides. Only then does anything
> reach the learner.

That last sentence is the thesis. Say it cleanly.

### 1:40 – 2:45 · The prototype, through Alfred

**Visual:** Click Alfred's row. The sheet slides in from the right.

**Narration:**
> Hanna clicks one learner. The class stays behind the panel, because she is
> triaging, not navigating away.

Point at the standing strip.

> Alfred is at fifty-eight percent readiness, eleven points below the class.
> Thirty-first percentile. And his momentum is negative six — his last ten
> attempts went worse than the ten before. That last number is the one the
> gradebook can never give her, because it only exists by comparison.

The sheet is triage by design: standing and the decision gate, nothing
else. The mastery instruments that need width live on the full record, so
hit **Open full record** (bottom of the sheet) to go deep.

Switch to the Mastery tab.

> Where is it going wrong? The radar shows it immediately. He is solid on
> Cloud Concepts, and IAM is the floor at forty-two percent across four
> attempts.

Switch to Activity, briefly.

> Every one of these numbers traces back to an append-only evidence ledger.
> Nothing here is a guess Kala cannot show its work for.

### 2:45 – 3:25 · Human-in-the-loop (the money shot)

**Visual:** Back to the Decide tab. Hit **Run analysis**.

**Narration:**
> Now Kala reads that twin and tells Hanna what it thinks Alfred needs. It
> sends the model a pseudonym and mastery numbers. It never sends his name.

Cards appear. Expand the first.

> Five recommendations, ordered by priority. And critically, every one shows
> the evidence it was derived from. Hanna is being asked to exercise
> professional judgement, and you cannot exercise judgement against a bare
> confidence score.

Read the top card aloud. Then:

> She has three options, and they are three real outcomes. Approve. Modify —
> if she thinks Kala picked the wrong activity, she rewrites it. Or decline.

**Click Modify.** Change the activity from Practice set to Guided lesson.
Type a reason.

> She disagrees with the activity. He is at thirty percent accuracy on IAM,
> so more practice would just rehearse the misconception. She changes it to
> a guided lesson and says why.

Confirm. Toast appears.

> That reason is stored. It is the audit trail, and it is training signal.

Now expand **Decision history**.

> And the one she declined earlier is still here, with her reason. Kala does
> not forget what a teacher decided.

**Cut to Alfred's screen.** Refresh.

> This is Alfred's workspace. "From your instructor." The guided lesson
> Hanna approved, in her words, with a path straight into the work. He does
> not see a confidence score. He does not see a risk label. He sees what his
> teacher asked him to do.

If you cut only one thing from this video, do not cut this cross-screen
moment. It is the entire argument.

### 3:25 – 3:50 · Impact and metrics

**Visual:** Back to the class overview, Trends tab.

**Narration:**
> Across the class: readiness over time from nightly snapshots, practice
> volume day by day, the mastery mix across every learner-and-skill cell,
> and the weakest skills across the cohort — which is Hanna's reteach list
> for next week.

Then the de-identify switch on the roster. **Turn it on.**

> And because student learning data is sensitive under the Data Privacy Act,
> the whole roster flips to pseudonyms with one switch — for screen-sharing,
> for a conference talk, for a video exactly like this one.

Leave it on for the rest of the recording.

### 3:50 – 4:10 · Scale and feasibility

**Visual:** Architecture slide, or the course switcher.

**Narration:**
> Kala enters through a standard LTI 1.3 launch, so it works with Blackboard
> and Canvas as they already are. Skills proposed for one course can be
> reused across others with an audit trail, so the second course to onboard
> costs less than the first. Every row is tenant-scoped and enforced by
> row-level security in Postgres. The same model that tracks a cloud
> certification tracks a board exam.

One sentence for the deferred surfaces, no screen:

> Researcher and administrator views are built on the same evidence log and
> are the next phase.

### 4:10 – 4:15 · Close

**Visual:** Kala logo.

> Blackboard and Canvas record learning. Kala measures it — and it leaves
> the teaching to the teacher.

---

## 5. Narration notes

- **Say "decides", not "approves".** Approving is a button. Deciding is a
  professional act, and the whole rubric line about ethics turns on the
  difference.
- **Never say "the AI knows".** Say "Kala estimates", "the evidence shows".
  You are making an epistemics claim and the judges will notice if you
  overclaim.
- **Do not say "at risk" out loud about a named student.** The product says
  "needs support" on purpose. Match it.
- Name the fallback if it fires. "Generated from mastery state directly"
  is a stronger answer than pretending a model ran.

---

## 6. Deliberately out of scope

**Researcher and admin surfaces.** Defer. Your professor's storyboard is a
single continuous journey through a teacher's eyes; a third persona breaks
it, and 4:15 does not have room. Mention in the scale beat, do not show.

**A sidebar nav.** The mockup has a persistent left rail and it does look
substantial. It is a real improvement and `shadcn`'s `Sidebar` primitive
would give it to you cheaply — but it is chrome, and the seven days before
a deadline are not when you restructure the shell. After the submission.

---

## 7. Known rough edges

Say these out loud to yourself before recording so nothing surprises you.

- The trend chart needs two or more days of readiness snapshots. With one
  day it renders an honest "not enough history yet" message. Seed
  accordingly.
- `learner_record` runs a cohort-wide query for the percentile: three extra
  selects per learner opened. Invisible at pilot scale, worth caching later.
- The heatmap has no small-screen strategy yet. It is in a tab now, so it
  is less exposed, but do not resize the window on camera.
- `useCreateIntervention` is wired end-to-end on the backend but has no UI
  yet. A teacher can only decide on Kala's proposals, not compose their own
  from scratch. That is a fine scope line for the demo — do not claim it.
