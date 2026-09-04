import { describe, expect, it } from "vitest";
import {
  validateAge,
  validateAttestedEntries,
  validateDisplayName,
  validateWeight,
} from "./validation";

describe("validateDisplayName", () => {
  it("trims the entered name", () => {
    expect(validateDisplayName("  Asha  ")).toEqual({ ok: true, value: "Asha" });
  });

  it("rejects an empty name", () => {
    expect(validateDisplayName("   ").ok).toBe(false);
  });

  it("rejects a name longer than the backend allows", () => {
    expect(validateDisplayName("a".repeat(161)).ok).toBe(false);
  });
});

describe("validateAge", () => {
  it("accepts whole completed years inside the range", () => {
    expect(validateAge("34")).toEqual({ ok: true, value: 34 });
    expect(validateAge("0")).toEqual({ ok: true, value: 0 });
    expect(validateAge("130")).toEqual({ ok: true, value: 130 });
  });

  it("rejects fractional and negative ages", () => {
    expect(validateAge("34.5").ok).toBe(false);
    expect(validateAge("-1").ok).toBe(false);
  });

  it("rejects ages above the range", () => {
    expect(validateAge("131").ok).toBe(false);
  });
});

describe("validateWeight", () => {
  it("keeps the typed decimal and its unit", () => {
    expect(validateWeight(" 61.5 ", "kg")).toEqual({
      ok: true,
      value: { entered: "61.5", unit: "kg", normalizedKg: 61.5 },
    });
  });

  it("normalizes pounds before checking the range", () => {
    const result = validateWeight("150", "lb");
    expect(result.ok).toBe(true);
    expect(result.ok && result.value.normalizedKg).toBeCloseTo(68.0389, 3);
    // 1 lb normalizes below the 0.5 kg floor.
    expect(validateWeight("1", "lb").ok).toBe(false);
  });

  it("rejects zero, non-numeric, and out-of-range weights", () => {
    expect(validateWeight("0", "kg").ok).toBe(false);
    expect(validateWeight("heavy", "kg").ok).toBe(false);
    expect(validateWeight("501", "kg").ok).toBe(false);
    expect(validateWeight("0.4", "kg").ok).toBe(false);
  });
});

describe("validateAttestedEntries", () => {
  it("drops blank rows and keeps the rest", () => {
    expect(validateAttestedEntries([" Asthma ", "", "Eczema"], false, "condition")).toEqual({
      ok: true,
      value: ["Asthma", "Eczema"],
    });
  });

  it("only accepts an empty set when none was declared explicitly", () => {
    expect(validateAttestedEntries(["", ""], false, "condition").ok).toBe(false);
    expect(validateAttestedEntries(["ignored"], true, "condition")).toEqual({
      ok: true,
      value: [],
    });
  });

  it("rejects entries above the backend limits", () => {
    expect(validateAttestedEntries(["x".repeat(241)], false, "condition").ok).toBe(false);
    expect(
      validateAttestedEntries(Array.from({ length: 101 }, (_, i) => `c${i}`), false, "condition")
        .ok,
    ).toBe(false);
  });
});
