import type { WeightUnit } from "../api/types";

export const MAX_DISPLAY_NAME_LENGTH = 160;
export const MAX_SEX_LENGTH = 40;
export const MIN_AGE = 0;
export const MAX_AGE = 130;
export const LB_TO_KG = 0.45359237;
export const MIN_WEIGHT_KG = 0.5;
export const MAX_WEIGHT_KG = 500;
export const MAX_ATTESTED_ENTRIES = 100;
export const MAX_ATTESTED_TITLE_LENGTH = 240;

export type Validated<T> = { ok: true; value: T } | { ok: false; error: string };

function invalid<T>(error: string): Validated<T> {
  return { ok: false, error };
}

export function validateDisplayName(raw: string): Validated<string> {
  const value = raw.trim();
  if (value === "") {
    return invalid("Enter the name to use for your own profile.");
  }
  if (value.length > MAX_DISPLAY_NAME_LENGTH) {
    return invalid(`Use ${MAX_DISPLAY_NAME_LENGTH} characters or fewer.`);
  }
  return { ok: true, value };
}

/**
 * Age is whole completed years. The backend stores the value with the date it
 * was reported and never increments it, so fractions and ranges fail here first.
 */
export function validateAge(raw: string): Validated<number> {
  const value = raw.trim();
  if (value === "") {
    return invalid("Enter an age in whole years.");
  }
  if (!/^\d+$/.test(value)) {
    return invalid("Enter age as whole completed years, without decimals.");
  }
  const parsed = Number(value);
  if (parsed < MIN_AGE || parsed > MAX_AGE) {
    return invalid(`Age must be between ${MIN_AGE} and ${MAX_AGE} years.`);
  }
  return { ok: true, value: parsed };
}

export interface ValidatedWeight {
  /** Kept as typed text so the exact decimal reaches the backend. */
  entered: string;
  unit: WeightUnit;
  normalizedKg: number;
}

export function validateWeight(raw: string, unit: WeightUnit): Validated<ValidatedWeight> {
  const entered = raw.trim();
  if (entered === "") {
    return invalid("Enter a weight.");
  }
  if (!/^\d*\.?\d+$/.test(entered)) {
    return invalid("Enter weight as a number, for example 61.5.");
  }
  const parsed = Number(entered);
  if (parsed <= 0) {
    return invalid("Weight must be greater than zero.");
  }
  const normalizedKg = unit === "kg" ? parsed : parsed * LB_TO_KG;
  if (normalizedKg < MIN_WEIGHT_KG || normalizedKg > MAX_WEIGHT_KG) {
    return invalid(
      `Weight must be between ${MIN_WEIGHT_KG} kg and ${MAX_WEIGHT_KG} kg ` +
        `(${round(MIN_WEIGHT_KG / LB_TO_KG)} lb and ${round(MAX_WEIGHT_KG / LB_TO_KG)} lb).`,
    );
  }
  return { ok: true, value: { entered, unit, normalizedKg } };
}

/**
 * An empty list is only accepted when the person explicitly declared none, so a
 * skipped step never looks like a "no conditions" answer.
 */
export function validateAttestedEntries(
  titles: string[],
  declaredNone: boolean,
  noun: string,
): Validated<string[]> {
  if (declaredNone) {
    return { ok: true, value: [] };
  }
  const value = titles.map((title) => title.trim()).filter((title) => title !== "");
  if (value.length === 0) {
    return invalid(`Add at least one ${noun}, or tick the "none" box.`);
  }
  if (value.length > MAX_ATTESTED_ENTRIES) {
    return invalid(`List no more than ${MAX_ATTESTED_ENTRIES} entries.`);
  }
  if (value.some((title) => title.length > MAX_ATTESTED_TITLE_LENGTH)) {
    return invalid(`Each entry must be ${MAX_ATTESTED_TITLE_LENGTH} characters or fewer.`);
  }
  return { ok: true, value };
}

function round(value: number): string {
  return value.toLocaleString("en", { maximumFractionDigits: 1 });
}
