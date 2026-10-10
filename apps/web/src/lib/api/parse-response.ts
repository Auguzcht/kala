import { z } from "zod";

export function parseApiResponse<T>(
  schema: z.ZodType<T>,
  data: unknown,
  endpoint: string,
): T {
  const parsed = schema.safeParse(data);
  if (!parsed.success) {
    if (import.meta.env.DEV) {
      console.error(`API response schema mismatch at ${endpoint}`, parsed.error);
    }
    throw parsed.error;
  }
  return parsed.data;
}
