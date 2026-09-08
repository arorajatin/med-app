import { afterEach, describe, expect, it, vi } from "vitest";
import { fileKind, validateFiles, validateImage } from "./validation";

afterEach(() => vi.unstubAllGlobals());

describe("upload validation", () => {
  it("permits an absent browser MIME but never trusts an unsupported one", () => {
    expect(fileKind(new File(["x"], "report.PDF"))).toBe("pdf");
    expect(fileKind(new File(["x"], "report.JPEG"))).toBe("image");
    expect(
      fileKind(new File(["x"], "report.png", { type: "text/html" })),
    ).toBeNull();
  });

  it("applies the exact total size and part ceilings", () => {
    const file = (bytes: number) =>
      new File([new Uint8Array(bytes)], "page.png", { type: "image/png" });
    expect(validateFiles([file(10_000_000), file(5_000_000)])).toBeNull();
    expect(validateFiles([file(10_000_000), file(5_000_001)])).toMatch(/15 MB/);
    expect(validateFiles(Array.from({ length: 20 }, () => file(1)))).toBeNull();
    expect(validateFiles(Array.from({ length: 21 }, () => file(1)))).toMatch(
      /20/,
    );
    expect(validateFiles([])).toMatch(/Choose/);
  });

  it.each(["valid", "oversized", "corrupt"])(
    "decodes %s images and revokes temporary previews",
    async (kind) => {
      const revoke = vi.fn();
      vi.stubGlobal(
        "URL",
        class extends URL {
          static createObjectURL = () => "blob:test";
          static revokeObjectURL = revoke;
        },
      );
      vi.stubGlobal(
        "Image",
        class {
          naturalWidth = kind === "oversized" ? 10_001 : 10_000;
          naturalHeight = 10;
          onload = () => {};
          onerror = () => {};
          set src(value: string) {
            void value;
            queueMicrotask(() =>
              kind === "corrupt" ? this.onerror() : this.onload(),
            );
          }
        },
      );
      const result = validateImage(new File(["x"], "page.png"));
      if (kind === "valid") await expect(result).resolves.toBeUndefined();
      else
        await expect(result).rejects.toThrow(
          kind === "corrupt" ? /could not be opened/ : /10,000/,
        );
      expect(revoke).toHaveBeenCalledWith("blob:test");
    },
  );
});
