export { Heatmap } from "@/features/instructor/components/Heatmap";
export { AtRiskList } from "@/features/instructor/components/AtRiskList";
export { StudentDrillDown } from "@/features/instructor/components/StudentDrillDown";
export { useHeatmap, useAtRisk, useStudentTwin } from "@/features/instructor/hooks/use-instructor";
export type {
  HeatmapData,
  HeatmapSkill,
  HeatmapStudent,
  HeatmapCell,
  AtRisk,
  AtRiskFlag,
  StudentTwin,
} from "@/features/instructor/schema/instructor.schema";
