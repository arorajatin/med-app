import { readOptionalEnv } from "../env";

/**
 * The terms the account manager accepts once for the whole account. The scope
 * is stored with the policy version, so changing either needs a new version.
 */
export const CONSENT_POLICY_VERSION: string =
  readOptionalEnv(import.meta.env.VITE_CONSENT_POLICY_VERSION) ?? "2026-07-01";

export const CONSENT_SCOPE: Record<string, boolean> = {
  ai_processing: true,
  document_extraction: true,
  reviewed_memory_chat: true,
};
