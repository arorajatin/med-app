import type { OnboardingStep } from "../api/types";

/** The step order the backend reports in `completed_steps` and `next_step`. */
export const ONBOARDING_STEPS: readonly OnboardingStep[] = [
  "self_profile",
  "health_context",
  "conditions",
  "medications",
];

export const STEP_LABELS: Record<OnboardingStep, string> = {
  self_profile: "Your name",
  health_context: "Age and weight",
  conditions: "Current conditions",
  medications: "Current medications",
};
