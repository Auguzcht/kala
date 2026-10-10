import { useQuery } from "@tanstack/react-query";
import { fetchBankStatus } from "@/features/bank/api/bank.api";

export function useBankStatus(courseId: string, enabled = true) {
  return useQuery({
    queryKey: ["bank", courseId, "status"],
    queryFn: () => fetchBankStatus(courseId),
    enabled: Boolean(courseId) && enabled,
    refetchInterval: (query) => query.state.data?.building ? 10_000 : false,
  });
}
