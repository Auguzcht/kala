export { Heatmap } from "@/features/instructor/components/Heatmap";
export { AtRiskList } from "@/features/instructor/components/AtRiskList";
export { StudentDrillDown } from "@/features/instructor/components/StudentDrillDown";
export { SkillReviewPanel } from "@/features/instructor/components/SkillReviewPanel";
export {
  useHeatmap,
  useAtRisk,
  useStudentTwin,
  useProposedSkills,
  useReviewProposedSkill,
} from "@/features/instructor/hooks/use-instructor";
export type {
  HeatmapData,
  HeatmapSkill,
  HeatmapStudent,
  HeatmapCell,
  AtRisk,
  AtRiskFlag,
  StudentTwin,
  ProposedSkill,
  ProposedSkills,
  ReviewResponse,
} from "@/features/instructor/schema/instructor.schema";
