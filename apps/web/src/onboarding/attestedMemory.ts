import type { AttestedCategory, MemoryFactRead } from "../api/types";

/** Provenance the backend writes for facts the account manager typed. */
export const USER_ATTESTED_PROVENANCE = "user_attested";

/**
 * The memory endpoint returns newest first. A declared list is one set the
 * person typed in order, so restore that order for editing and display.
 */
export function attestedTitles(facts: MemoryFactRead[], category: AttestedCategory): string[] {
  return facts
    .filter((fact) => fact.provenance === USER_ATTESTED_PROVENANCE && fact.category === category)
    .slice()
    .sort((left, right) => left.created_at.localeCompare(right.created_at))
    .map((fact) => fact.title);
}
