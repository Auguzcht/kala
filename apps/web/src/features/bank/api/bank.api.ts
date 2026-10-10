import { api } from "@/lib/api/client";
import { bankStatusSchema, type BankStatus } from "@/features/bank/schema/bank-status.schema";

export async function fetchBankStatus(courseId: string): Promise<BankStatus> {
  const data = await api<unknown>(`/courses/${courseId}/bank/status`);
  return bankStatusSchema.parse(data);
}
