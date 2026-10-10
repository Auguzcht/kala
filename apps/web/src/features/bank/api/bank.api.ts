import { api } from "@/lib/api/client";
import { parseApiResponse } from "@/lib/api/parse-response";
import { bankStatusSchema, type BankStatus } from "@/features/bank/schema/bank-status.schema";

export async function fetchBankStatus(courseId: string): Promise<BankStatus> {
  const data = await api<unknown>(`/courses/${courseId}/bank/status`);
  return parseApiResponse(bankStatusSchema, data, `/courses/${courseId}/bank/status`);
}
