import { vi } from "vitest";
import { setAccessTokenProvider } from "../api/client";

export interface RecordedCall {
  method: string;
  path: string;
  body: unknown;
}

type Handler = (call: RecordedCall) => { status?: number; body: unknown };

/**
 * Routes `fetch` calls by "METHOD /path" so a test states only the API
 * responses it cares about, and records what the client sent.
 */
export function mockApi(handlers: Record<string, Handler | unknown>) {
  const calls: RecordedCall[] = [];
  setAccessTokenProvider(async () => "test-access-token");
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    const path = url.replace(/^\/api/, "");
    const body = init?.body === undefined ? undefined : JSON.parse(String(init.body));
    const call: RecordedCall = { method, path, body };
    calls.push(call);

    const handler = handlers[`${method} ${path}`];
    if (handler === undefined) {
      return new Response(JSON.stringify({ detail: `No handler for ${method} ${path}` }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      });
    }
    const result = typeof handler === "function" ? (handler as Handler)(call) : { body: handler };
    return new Response(JSON.stringify(result.body), {
      status: result.status ?? 200,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return { calls };
}

export const SELF_PROFILE = {
  id: "profile_1",
  display_name: "Asha",
  relationship: "self",
  sex: null,
  created_at: "2026-07-01T00:00:00Z",
  updated_at: "2026-07-01T00:00:00Z",
};

export function onboardingState(
  overrides: Partial<{
    status: string;
    next_step: string | null;
    completed_steps: string[];
    self_profile: typeof SELF_PROFILE | null;
  }> = {},
) {
  return {
    status: "in_progress",
    next_step: "self_profile",
    completed_steps: [],
    self_profile: null,
    ...overrides,
  };
}
