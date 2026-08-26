export { Heatmap } from "@/features/instructor/components/Heatmap";
export { AtRiskList } from "@/features/instructor/components/AtRiskList";
export { StudentDrillDown } from "@/features/instructor/components/StudentDrillDown";
export { SkillReviewPanel } from "@/features/instructor/components/SkillReviewPanel";
export { AutoMatchedSection } from "@/features/instructor/components/AutoMatchedSection";
export {
  useHeatmap,
  useAtRisk,
  useStudentTwin,
  useProposedSkills,
  useReviewProposedSkill,
  useProposeSkills,
  useAutoMatchedSkills,
  useDetachAutoMatchedSkill,
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
  ProposeSkillsResult,
  AutoMatchedSkill,
  AutoMatchedSkills,
  DetachResponse,
} from "@/features/instructor/schema/instructor.schema";
