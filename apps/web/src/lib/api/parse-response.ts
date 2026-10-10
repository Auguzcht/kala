import { z } from "zod";

function findUnknownFields(raw: unknown, parsed: unknown, path = ""): string[] {
  if (Array.isArray(raw) && Array.isArray(parsed)) {
    return raw.flatMap((value, index) =>
      findUnknownFields(value, parsed[index], `${path}[${index}]`),
    );
  }
  if (
    raw === null || parsed === null ||
    typeof raw !== "object" || typeof parsed !== "object" ||
    Array.isArray(raw) || Array.isArray(parsed)
  ) return [];

  const projected = parsed as Record<string, unknown>;
  return Object.entries(raw as Record<string, unknown>).flatMap(([key, value]) => {
    const fieldPath = path ? `${path}.${key}` : key;
    if (!(key in projected)) return [fieldPath];
    return findUnknownFields(value, projected[key], fieldPath);
  });
}

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
  if (import.meta.env.DEV) {
    const unknownFields = findUnknownFields(data, parsed.data);
    if (unknownFields.length > 0) {
      console.warn(`API response has unknown fields at ${endpoint}`, unknownFields);
    }
  }
  return parsed.data;
}
