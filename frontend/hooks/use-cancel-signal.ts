import { useMutation, useQueryClient } from "@tanstack/react-query";

import { cancelSignal } from "@/services/signals";

/** ADR-169 - cancels a draft or an unfilled signal. The detail page shows the
 *  returned signal at once; lists refetch. */
export function useCancelSignal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => cancelSignal(id),
    onSuccess: (signal) => {
      queryClient.setQueryData(["signal", signal.id], signal);
      void queryClient.invalidateQueries({ queryKey: ["signals"] });
    },
  });
}
