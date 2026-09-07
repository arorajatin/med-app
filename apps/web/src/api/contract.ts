/**
 * Ties the hand-written types in `./types.ts` to the generated contract in
 * `contracts/api.ts`, so `npm run typecheck` fails when the backend's OpenAPI
 * document and this client stop agreeing.
 *
 * Two checks, because each catches something the other misses:
 * - assignability catches a field whose type changed;
 * - matching key sets catch a field the backend added, removed, or renamed.
 *
 * Assignability runs one way only. The hand-written types deliberately narrow
 * some strings the backend declares as plain text, such as `onboarding_status`.
 */
import type { components } from "../../../../contracts/api";
import type {
  AccountRead,
  AttestedMemoryRead,
  MemoryFactRead,
  MemoryRead,
  OnboardingRead,
  ProfileHealthContextRead,
  ProfileHealthContextSummary,
  ProfileRead,
} from "./types";

type Schemas = components["schemas"];

/** Fails to compile unless `Mirror` can stand in for the generated `Generated`. */
type Matches<Mirror extends Generated, Generated> = SameKeys<Mirror, Generated>;

type SameKeys<Mirror, Generated> = [keyof Mirror] extends [keyof Generated]
  ? [keyof Generated] extends [keyof Mirror]
    ? true
    : { missingFromMirror: Exclude<keyof Generated, keyof Mirror> }
  : { notInTheContract: Exclude<keyof Mirror, keyof Generated> };

export type AccountReadMatches = Matches<AccountRead, Schemas["AccountRead"]>;
export type ProfileReadMatches = Matches<ProfileRead, Schemas["ProfileRead"]>;
export type OnboardingReadMatches = Matches<OnboardingRead, Schemas["OnboardingRead"]>;
export type ProfileHealthContextReadMatches = Matches<
  ProfileHealthContextRead,
  Schemas["ProfileHealthContextRead"]
>;
export type ProfileHealthContextSummaryMatches = Matches<
  ProfileHealthContextSummary,
  Schemas["ProfileHealthContextSummary"]
>;
export type MemoryFactReadMatches = Matches<MemoryFactRead, Schemas["MemoryFactRead"]>;
export type MemoryReadMatches = Matches<MemoryRead, Schemas["MemoryRead"]>;
export type AttestedMemoryReadMatches = Matches<AttestedMemoryRead, Schemas["AttestedMemoryRead"]>;
