import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
  OnboardingManifest,
  OnboardingResult,
  OnboardingResultSchema,
} from "@/types/onboarding";

/** Preview onboarding — resolve packs + scaffold with no side effects. */
export function useOnboardPreview() {
  return useMutation<OnboardingResult, Error, OnboardingManifest>({
    mutationFn: async (manifest) => {
      const data = await apiFetch<unknown>("/onboarding/preview", {
        method: "POST",
        body: JSON.stringify(manifest),
      });
      return OnboardingResultSchema.parse(data);
    },
  });
}

/** Onboard a project — scaffold + registry hand-off at the Requirements phase. */
export function useOnboard() {
  return useMutation<OnboardingResult, Error, OnboardingManifest>({
    mutationFn: async (manifest) => {
      const data = await apiFetch<unknown>("/onboarding/", {
        method: "POST",
        body: JSON.stringify(manifest),
      });
      return OnboardingResultSchema.parse(data);
    },
  });
}
