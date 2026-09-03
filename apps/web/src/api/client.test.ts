import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, request } from "./client";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("request", () => {
  it("sends the bearer token and the JSON body", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { id: "acc_1" }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await request<{ id: string }>("/account", {
      method: "POST",
      token: "user_1",
      body: { policy_version: "2026-07-01" },
    });

    expect(result).toEqual({ id: "acc_1" });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit & { headers: Record<string, string> }];
    expect(url).toBe("/api/account");
    expect(init.headers.Authorization).toBe("Bearer user_1");
    expect(init.headers["Content-Type"]).toBe("application/json");
    expect(init.body).toBe(JSON.stringify({ policy_version: "2026-07-01" }));
  });

  it("surfaces a string detail from the API", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(409, { detail: "This account already has a self profile." })),
    );

    await expect(request("/profiles", { token: "user_1" })).rejects.toMatchObject({
      status: 409,
      message: "This account already has a self profile.",
    });
  });

  it("joins validation messages from a 422 and drops the pydantic prefix", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(422, {
          detail: [{ msg: "Value error, At least one reported age or weight value is required." }],
        }),
      ),
    );

    await expect(request("/profiles/p1/health-context", { token: "user_1" })).rejects.toThrow(
      "At least one reported age or weight value is required.",
    );
  });

  it("reports an unreachable server without leaking the network error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    const error = await request("/account", { token: "user_1" }).catch((cause) => cause);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(0);
  });
});
