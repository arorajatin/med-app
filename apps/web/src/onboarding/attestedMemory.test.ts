import { describe, expect, it } from "vitest";
import type { MemoryFactRead } from "../api/types";
import { attestedTitles } from "./attestedMemory";

function fact(overrides: Partial<MemoryFactRead>): MemoryFactRead {
  return {
    id: "fact",
    profile_id: "profile_1",
    source_record_id: null,
    source_candidate_id: null,
    source_reference_id: null,
    provenance: "user_attested",
    category: "condition",
    title: "Asthma",
    details: {},
    is_active: true,
    created_at: "2026-07-01T00:00:00Z",
    ...overrides,
  };
}

describe("attestedTitles", () => {
  it("keeps the order the person declared, oldest first", () => {
    const titles = attestedTitles(
      [
        fact({ id: "b", title: "Seasonal allergic rhinitis", created_at: "2026-07-01T00:00:02Z" }),
        fact({ id: "a", title: "Asthma", created_at: "2026-07-01T00:00:01Z" }),
      ],
      "condition",
    );
    expect(titles).toEqual(["Asthma", "Seasonal allergic rhinitis"]);
  });

  it("keeps only this category's user-attested facts", () => {
    const titles = attestedTitles(
      [
        fact({ id: "a", title: "Asthma" }),
        fact({ id: "b", title: "Salbutamol", category: "medication" }),
        fact({ id: "c", title: "Extracted condition", provenance: "document_extracted" }),
      ],
      "condition",
    );
    expect(titles).toEqual(["Asthma"]);
  });
});
