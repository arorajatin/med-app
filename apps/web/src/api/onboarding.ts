import { request } from "./client";
import type {
  AccountRead,
  AttestedCategory,
  AttestedEntryInput,
  AttestedMemoryRead,
  ConsentRead,
  MemoryRead,
  OnboardingRead,
  ProfileHealthContextRead,
  ProfileRead,
  WeightUnit,
} from "./types";

export function getAccount(token: string): Promise<AccountRead> {
  return request<AccountRead>("/account", { token });
}

export function getOnboarding(token: string): Promise<OnboardingRead> {
  return request<OnboardingRead>("/account/onboarding", { token });
}

export function acceptConsent(
  token: string,
  input: { policyVersion: string; acceptedScope: Record<string, unknown> },
): Promise<ConsentRead> {
  return request<ConsentRead>("/account/consents", {
    method: "POST",
    token,
    body: { policy_version: input.policyVersion, accepted_scope: input.acceptedScope },
  });
}

export function putSelfProfile(
  token: string,
  input: { displayName: string; sex: string | null },
): Promise<ProfileRead> {
  return request<ProfileRead>("/account/onboarding/self-profile", {
    method: "PUT",
    token,
    body: { display_name: input.displayName, sex: input.sex },
  });
}

export function createHealthContext(
  token: string,
  profileId: string,
  input: { reportedAge: number; enteredWeight: string; weightUnit: WeightUnit; reportedAt: string },
): Promise<ProfileHealthContextRead> {
  return request<ProfileHealthContextRead>(`/profiles/${profileId}/health-context`, {
    method: "POST",
    token,
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
  token: string,
  profileId: string,
  category: AttestedCategory,
  entries: AttestedEntryInput[],
): Promise<AttestedMemoryRead> {
  return request<AttestedMemoryRead>(`/profiles/${profileId}/${ATTESTED_PATHS[category]}`, {
    method: "PUT",
    token,
    body: { entries: entries.map((entry) => ({ title: entry.title, details: entry.details ?? {} })) },
  });
}

export function getMemory(token: string, profileId: string): Promise<MemoryRead> {
  return request<MemoryRead>(`/profiles/${profileId}/memory`, { token });
}
