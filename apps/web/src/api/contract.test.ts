// @vitest-environment node
import { fileURLToPath } from "node:url";
import ts from "typescript";
import { describe, expect, it } from "vitest";

const contractPath = fileURLToPath(new URL("./contract.ts", import.meta.url));
const generatedPath = fileURLToPath(new URL("../../../../contracts/api.ts", import.meta.url));

/** Compile the real checks against an in-memory edit of the generated contract. */
function diagnosticsFor(displayNameField: string) {
  const options = { strict: true, noEmit: true, skipLibCheck: true, types: [] };
  const host = ts.createCompilerHost(options);
  const readFile = host.readFile;
  host.readFile = (fileName) => {
    const source = readFile(fileName);
    if (fileName !== generatedPath || source === undefined) {
      return source;
    }
    return source.replace(/(ProfileRead: \{[\s\S]*?)display_name: string;/, `$1${displayNameField}`);
  };
  const program = ts.createProgram([contractPath], options, host);
  return ts.getPreEmitDiagnostics(program);
}

describe("API contract checks", () => {
  it("accepts the current contract and its deliberately narrowed string types", () => {
    expect(diagnosticsFor("display_name: string;")).toEqual([]);
  });

  it.each([
    ["removed field", ""],
    ["added optional field", "display_name: string; nickname?: string;"],
    ["changed field type", "display_name: number;"],
  ])("rejects a %s in the generated response", (_, field) => {
    const diagnostics = diagnosticsFor(field);
    expect(diagnostics.some((diagnostic) => diagnostic.file?.fileName === contractPath)).toBe(true);
  });
});
