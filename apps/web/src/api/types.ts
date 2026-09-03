/** Mirrors the response models in `apps/api/app/schemas.py`. */

export type OnboardingStep =
  | "consent"
  | "self_profile"
  | "health_context"
  | "conditions"
  | "medications";

export type OnboardingStatus = "not_started" | "in_progress" | "completed";

export type AttestedCategory = "condition" | "medication";

export type WeightUnit = "kg" | "lb";

export interface AccountRead {
  id: string;
  onboarding_status: OnboardingStatus;
  created_at: string;
  updated_at: string;
}

export interface ProfileRead {
  id: string;
  display_name: string;
  relationship: string;
  sex: string | null;
  created_at: string;
  updated_at: string;
}

export interface OnboardingRead {
  status: OnboardingStatus;
  next_step: OnboardingStep | null;
  completed_steps: OnboardingStep[];
  self_profile: ProfileRead | null;
}

export interface ConsentRead {
  id: string;
  policy_version: string;
  accepted_scope: Record<string, unknown>;
  accepted_at: string;
}

export interface ProfileHealthContextRead {
  id: string;
  profile_id: string;
  reported_age: number | null;
  age_reported_at: string | null;
  entered_weight: string | null;
  weight_unit: WeightUnit | null;
  normalized_weight_kg: string | null;
  weight_reported_at: string | null;
  created_at: string;
}

export interface MemoryFactRead {
  id: string;
  profile_id: string;
  source_record_id: string | null;
  source_candidate_id: string | null;
  source_reference_id: string | null;
  provenance: string;
  category: string;
  title: string;
  details: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
}

export interface MemoryRead {
  profile: ProfileRead;
  facts: MemoryFactRead[];
}

export interface AttestedMemoryRead {
  category: AttestedCategory;
  declared_at: string;
  facts: MemoryFactRead[];
}

export interface AttestedEntryInput {
  title: string;
  details?: Record<string, unknown>;
}
