import { z } from "zod";
import {
  evidenceEventSchema,
  masteryBandSchema,
  twinSchema,
  twinSkillSchema,
} from "@/features/twin/schema/twin.schema";

export const heatmapSkillSchema = z.object({
  skillId: z.string(),
  name: z.string(),
  bloomLevel: z.string().nullable().optional(),
  cohortBand: masteryBandSchema,
  cohortEstimate: z.number().nullable(),
});

export const heatmapStudentSchema = z.object({
  userId: z.string(),
  displayName: z.string(),
  pseudonym: z.string(),
  initials: z.string(),
});

export const heatmapCellSchema = z.object({
  userId: z.string(),
  skillId: z.string(),
  estimate: z.number().nullable(),
  attempts: z.number(),
  band: masteryBandSchema,
});

export const heatmapSchema = z.object({
  courseId: z.string(),
  cohortReadiness: z.number().nullable(),
  skills: z.array(heatmapSkillSchema),
  students: z.array(heatmapStudentSchema),
  cells: z.array(heatmapCellSchema),
});

export const atRiskFlagSchema = z.object({
  userId: z.string(),
  displayName: z.string(),
  pseudonym: z.string(),
  initials: z.string(),
  reason: z.string(),
  daysInactive: z.number().nullable(),
  evidenceCount: z.number(),
  weakestSkillNames: z.array(z.string()),
});

export const atRiskSchema = z.object({
  courseId: z.string(),
  flags: z.array(atRiskFlagSchema),
});

// Instructor's read of one student's twin: the twin shape + pseudonym.
export const studentTwinSchema = twinSchema.extend({ pseudonym: z.string() });

// HITL skill proposals awaiting review (docs/SKILL_PIPELINE.md). Rows come
// back snake_case from the review endpoint (DB-shaped, not generated types).
export const proposedSkillSchema = z.object({
  id: z.string(),
  name: z.string(),
  bloom_level: z.string(),
  blueprint_weight: z.number(),
  proposed_source: z.string().nullable(),
});

export const proposedSkillsSchema = z.object({
  courseId: z.string(),
  proposed: z.array(proposedSkillSchema),
});

export const reviewResponseSchema = z.object({
  skillId: z.string(),
  status: z.enum(["approved", "rejected"]),
});

// On-demand proposal trigger (POST /courses/{id}/skills/propose). Skipped
// shape when the course already has skills; full shape when it ran.
export const proposeSkillsResultSchema = z.object({
  skipped: z.boolean(),
  reason: z.string().optional(),
  modulesProcessed: z.number().optional(),
  modulesSkipped: z.number().optional(),
  proposed: z.number().optional(),
  auto_approved: z.number().optional(),
  flagged_possible_duplicate: z.number().optional(),
  flagged_in_batch_duplicate: z.number().optional(),
  insertFailed: z.number().optional(),
});

// Live skills inherited via cross-course auto-match (canonical_skill_id
// set). Auditable reuse: the instructor can see what was inherited and
// detach it to tune for this course.
export const autoMatchedSkillSchema = z.object({
  id: z.string(),
  name: z.string(),
  bloom_level: z.string(),
  blueprint_weight: z.number(),
  module_ref: z.string().nullable(),
  proposed_source: z.string().nullable(),
  canonical_skill_id: z.string().nullable(),
});

export const autoMatchedSkillsSchema = z.object({
  courseId: z.string(),
  autoMatched: z.array(autoMatchedSkillSchema),
});

export const detachResponseSchema = z.object({
  skillId: z.string(),
  status: z.enum(["proposed"]),
  detached: z.literal(true),
});

export type HeatmapSkill = z.infer<typeof heatmapSkillSchema>;
export type HeatmapStudent = z.infer<typeof heatmapStudentSchema>;
export type HeatmapCell = z.infer<typeof heatmapCellSchema>;
export type HeatmapData = z.infer<typeof heatmapSchema>;
export type AtRiskFlag = z.infer<typeof atRiskFlagSchema>;
export type AtRisk = z.infer<typeof atRiskSchema>;
export type StudentTwin = z.infer<typeof studentTwinSchema>;
export type ProposedSkill = z.infer<typeof proposedSkillSchema>;
export type ProposedSkills = z.infer<typeof proposedSkillsSchema>;
export type ReviewResponse = z.infer<typeof reviewResponseSchema>;
export type ProposeSkillsResult = z.infer<typeof proposeSkillsResultSchema>;
export type AutoMatchedSkill = z.infer<typeof autoMatchedSkillSchema>;
export type AutoMatchedSkills = z.infer<typeof autoMatchedSkillsSchema>;
export type DetachResponse = z.infer<typeof detachResponseSchema>;

// ---- Cohort reads (roster, stats, learner record) -------------------------
// The class overview was one heatmap and one ring. These three shapes are
// what a teacher actually scans a class by. All three come from
// app/twin/cohort.py on the backend; the client never computes mastery.

// Learner status is a triage word, not a grade. "needs-support" is the only
// flag and it names the support, never the person (DESIGN.md).
export const learnerStatusSchema = z.enum([
  "on-track",
  "developing",
  "needs-support",
  "not-started",
]);

export const rosterRowSchema = z.object({
  userId: z.string(),
  // Real name for the teacher of record; pseudonym always travels alongside
  // so the UI can flip to de-identified mode for screen-sharing and so
  // nothing downstream has to look one up.
  displayName: z.string(),
  pseudonym: z.string(),
  initials: z.string(),
  readiness: z.number().nullable(),
  band: masteryBandSchema,
  attempts: z.number(),
  evidenceCount: z.number(),
  accuracy: z.number().nullable(),
  lastActiveAt: z.string().nullable(),
  daysInactive: z.number().nullable(),
  weakestSkillName: z.string().nullable(),
  skillsWithEvidence: z.number(),
  skillsTotal: z.number(),
  status: learnerStatusSchema,
});

export const rosterSchema = z.object({
  courseId: z.string(),
  students: z.array(rosterRowSchema),
});

export const cohortStatsSchema = z.object({
  courseId: z.string(),
  learners: z.number(),
  activeLearners: z.number(),
  startedLearners: z.number(),
  notStartedLearners: z.number(),
  cohortReadiness: z.number().nullable(),
  medianReadiness: z.number().nullable(),
  accuracy: z.number().nullable(),
  evidenceCount: z.number(),
  medianLatencyMs: z.number().nullable(),
  hintsUsed: z.number(),
  skillsTracked: z.number(),
  skillsCovered: z.number(),
  bandDistribution: z.array(z.object({ band: masteryBandSchema, count: z.number() })),
  bloomCoverage: z.array(
    z.object({ level: z.string(), skills: z.number(), estimate: z.number().nullable() })
  ),
  skillBreakdown: z.array(
    z.object({
      skillId: z.string(),
      name: z.string(),
      bloomLevel: z.string().nullable(),
      moduleRef: z.string().nullable(),
      estimate: z.number().nullable(),
      learnersWithEvidence: z.number(),
      band: masteryBandSchema,
    })
  ),
  readinessTrend: z.array(
    z.object({ date: z.string(), readiness: z.number(), learners: z.number() })
  ),
  activitySeries: z.array(
    z.object({
      date: z.string(),
      correct: z.number(),
      missed: z.number(),
      ungraded: z.number(),
    })
  ),
  decisions: z.object({
    pending: z.number(),
    approved: z.number(),
    rejected: z.number(),
    completed: z.number(),
  }),
});

export const learnerRecordSchema = z.object({
  courseId: z.string(),
  userId: z.string(),
  displayName: z.string(),
  pseudonym: z.string(),
  initials: z.string(),
  readiness: z.number().nullable(),
  band: masteryBandSchema,
  cohortReadiness: z.number().nullable(),
  percentile: z.number().nullable(),
  accuracy: z.number().nullable(),
  // Last 10 graded attempts vs the 10 before. A learner at 45% climbing
  // needs a different conversation than one at 45% sliding.
  momentum: z.number().nullable(),
  attempts: z.number(),
  evidenceCount: z.number(),
  hintsUsed: z.number(),
  lastActiveAt: z.string().nullable(),
  daysInactive: z.number().nullable(),
  status: learnerStatusSchema,
  skills: z.array(twinSkillSchema.extend({ lastSeen: z.string().nullable().optional() })),
  activityByType: z.array(z.object({ type: z.string(), count: z.number() })),
  activitySeries: z.array(
    z.object({
      date: z.string(),
      correct: z.number(),
      missed: z.number(),
      ungraded: z.number(),
    })
  ),
  readinessTrend: z.array(z.object({ date: z.string(), readiness: z.number() })),
  evidence: z.array(evidenceEventSchema),
});

// ---- Prescriptive recommendations (the teaching gate) ---------------------
// AI proposes, the instructor decides, and only a decided row reaches the
// learner. "modified" stays distinct from "approved" on purpose: how often
// a teacher edits the AI rather than taking it as written is one of the
// study's research questions, and it is only answerable if they are
// different values.

export const recommendationStatusSchema = z.enum([
  "suggested",
  "approved",
  "modified",
  "rejected",
  "completed",
]);

export const recommendationKindSchema = z.enum([
  "practice",
  "lesson",
  "flashcards",
  "tutor",
  "diagnostic",
  "outreach",
]);

export const recommendationSchema = z.object({
  id: z.string(),
  userId: z.string(),
  courseId: z.string(),
  skillId: z.string().nullable(),
  skillName: z.string().nullable(),
  title: z.string(),
  kind: recommendationKindSchema,
  priority: z.enum(["high", "medium", "low"]),
  rationale: z.string().nullable(),
  // The receipts. A recommendation with no evidence is not shown — "never a
  // bare score" (DESIGN.md).
  evidence: z.array(z.object({ label: z.string(), detail: z.string() })),
  status: recommendationStatusSchema,
  confidence: z.number().nullable(),
  expectedGain: z.number().nullable(),
  // The model id, or "heuristic" when the deterministic fallback produced
  // it, or "instructor" when a human wrote it. Shown, not hidden.
  source: z.string().nullable(),
  decidedBy: z.string().nullable(),
  decidedAt: z.string().nullable(),
  decisionNote: z.string().nullable(),
  instructorNote: z.string().nullable(),
  createdAt: z.string().nullable(),
});

export const recommendationListSchema = z.object({
  courseId: z.string(),
  userId: z.string(),
  recommendations: z.array(recommendationSchema),
});

export const generateRecommendationsSchema = z.object({
  courseId: z.string(),
  userId: z.string(),
  generated: z.number(),
  source: z.string().optional(),
  recommendations: z.array(recommendationSchema),
});

export type LearnerStatus = z.infer<typeof learnerStatusSchema>;
export type RosterRow = z.infer<typeof rosterRowSchema>;
export type Roster = z.infer<typeof rosterSchema>;
export type CohortStats = z.infer<typeof cohortStatsSchema>;
export type LearnerRecord = z.infer<typeof learnerRecordSchema>;
export type Recommendation = z.infer<typeof recommendationSchema>;
export type RecommendationList = z.infer<typeof recommendationListSchema>;
export type RecommendationStatus = z.infer<typeof recommendationStatusSchema>;
export type RecommendationKind = z.infer<typeof recommendationKindSchema>;
export type GenerateRecommendations = z.infer<typeof generateRecommendationsSchema>;
