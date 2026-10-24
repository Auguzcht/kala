import type { TutorAttachment } from "@/features/tutor/schema/tutor.schema";

export type TutorFileUploadResult = {
  uploaded: { file: File; attachment: TutorAttachment }[];
  failed: File[];
};
export type StagedTutorFile = { id: string; file: File; failed?: boolean };
export const TEXT_PREVIEW_BYTES = 128 * 1024;
export const canPreviewTutorFile = (file: File) =>
  /\.(txt|md)$/i.test(file.name);
export function tutorFileSize(bytes: number) {
  return bytes < 1024
    ? `${bytes} B`
    : bytes < 1024 * 1024
      ? `${(bytes / 1024).toFixed(1)} KB`
      : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
