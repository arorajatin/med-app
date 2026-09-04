import { request } from "./client";
import type {
  AccountRead,
  AttestedCategory,
  AttestedEntryInput,
  AttestedMemoryRead,
  MemoryRead,
  OnboardingRead,
  ProfileHealthContextRead,
  ProfileRead,
  WeightUnit,
} from "./types";

export function getAccount(): Promise<AccountRead> {
  return request<AccountRead>("/account");
}

export function getOnboarding(): Promise<OnboardingRead> {
  return request<OnboardingRead>("/account/onboarding");
}

export function putSelfProfile(input: {
  displayName: string;
  sex: string | null;
}): Promise<ProfileRead> {
  return request<ProfileRead>("/account/onboarding/self-profile", {
    method: "PUT",
    body: { display_name: input.displayName, sex: input.sex },
  });
}

export function createHealthContext(
  profileId: string,
  input: { reportedAge: number; enteredWeight: string; weightUnit: WeightUnit; reportedAt: string },
): Promise<ProfileHealthContextRead> {
  return request<ProfileHealthContextRead>(`/profiles/${profileId}/health-context`, {
    method: "POST",
    body: {
      reported_age: input.reportedAge,
      age_reported_at: input.reportedAt,
      entered_weight: input.enteredWeight,
      weight_unit: input.weightUnit,
      weight_reported_at: input.reportedAt,
    },
  });
}

/** The route paths use the plural category, matching the backend. */
const ATTESTED_PATHS: Record<AttestedCategory, string> = {
  condition: "attested-conditions",
  medication: "attested-medications",
};

export function declareAttestedMemory(
  profileId: string,
  category: AttestedCategory,
  entries: AttestedEntryInput[],
): Promise<AttestedMemoryRead> {
  return request<AttestedMemoryRead>(`/profiles/${profileId}/${ATTESTED_PATHS[category]}`, {
    method: "PUT",
    body: {
      entries: entries.map((entry) => ({ title: entry.title, details: entry.details ?? {} })),
    },
  });
}

export function getMemory(profileId: string): Promise<MemoryRead> {
  return request<MemoryRead>(`/profiles/${profileId}/memory`);
}
