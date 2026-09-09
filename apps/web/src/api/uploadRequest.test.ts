import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mockUploadTransport } from "../test/uploadMock";
import { setAccessTokenProvider, uploadRequest } from "./client";

beforeEach(() => setAccessTokenProvider(async () => "fresh-token"));
afterEach(() => vi.unstubAllGlobals());

describe("multipart upload transport", () => {
  it("refuses a missing session before any upload begins", async () => {
    const xhrs = mockUploadTransport();
    setAccessTokenProvider(async () => null);
    await expect(
      uploadRequest(
        "/ingestions/direct-file",
        new FormData(),
        vi.fn(),
        new AbortController().signal,
      ),
    ).rejects.toMatchObject({ status: 401 });
    expect(xhrs).toHaveLength(0);
  });

  it.each(["network", "timeout"])(
    "offers a safe error for %s failures",
    async (kind) => {
      const xhrs = mockUploadTransport();
      const pending = uploadRequest(
        "/ingestions/direct-file",
        new FormData(),
        vi.fn(),
        new AbortController().signal,
      );
      await Promise.resolve();
      if (kind === "network") xhrs[0]!.onerror?.();
      else xhrs[0]!.ontimeout?.();
      await expect(pending).rejects.toMatchObject({
        status: 0,
        message: expect.stringMatching(/connection/),
      });
    },
  );

  it("uses the current token on a retry and never sets a JSON content type", async () => {
    const xhrs = mockUploadTransport();
    for (const token of ["first-token", "rotated-token"]) {
      setAccessTokenProvider(async () => token);
      const pending = uploadRequest(
        "/ingestions/camera",
        new FormData(),
        vi.fn(),
        new AbortController().signal,
      );
      await Promise.resolve();
      const xhr = xhrs.at(-1)!;
      expect(xhr.setRequestHeader).toHaveBeenCalledExactlyOnceWith(
        "Authorization",
        `Bearer ${token}`,
      );
      xhr.respond();
      await pending;
    }
  });

  it("does not send private data when aborted while obtaining a token", async () => {
    const xhrs = mockUploadTransport();
    const controller = new AbortController();
    const pending = uploadRequest(
      "/ingestions/direct-file",
      new FormData(),
      vi.fn(),
      controller.signal,
    );
    controller.abort();
    await expect(pending).rejects.toMatchObject({ name: "AbortError" });
    expect(xhrs).toHaveLength(0);
  });
});
