import { afterEach, describe, expect, it, vi } from "vitest";
import {
  clearAuthRedirectError,
  currentAccessToken,
  isAuthConfigured,
  onSessionChange,
  readAuthRedirectError,
} from "./session";

function visit(url: string): void {
  window.history.replaceState({}, "", url);
}

afterEach(() => {
  visit("/");
});

describe("readAuthRedirectError", () => {
  it("finds nothing on an ordinary visit", () => {
    visit("/");

    expect(readAuthRedirectError()).toBeNull();
  });

  it("prefers the provider's description", () => {
    visit("/?error=access_denied&error_description=The+user+denied+access");

    expect(readAuthRedirectError()).toBe("The user denied access");
  });

  it("falls back to the error code when there is no description", () => {
    visit("/?error=access_denied");

    expect(readAuthRedirectError()).toBe("Sign-in did not complete (access_denied).");
  });

  it("reads a failure returned in the URL fragment", () => {
    visit("/#error=server_error&error_description=Provider+is+not+enabled");

    expect(readAuthRedirectError()).toBe("Provider is not enabled");
  });
});

describe("clearAuthRedirectError", () => {
  it("removes only the error parameters", () => {
    visit("/?error=access_denied&error_description=Nope&next=%2Ffeed");

    clearAuthRedirectError();

    expect(window.location.search).toBe("?next=%2Ffeed");
    expect(readAuthRedirectError()).toBeNull();
  });

  it("clears a failure left in the fragment", () => {
    visit("/#error=server_error");

    clearAuthRedirectError();

    expect(window.location.hash).toBe("");
  });

  it("leaves a clean URL untouched", () => {
    visit("/?next=%2Ffeed");
    const replaceState = vi.spyOn(window.history, "replaceState");

    clearAuthRedirectError();

    expect(replaceState).not.toHaveBeenCalled();
    replaceState.mockRestore();
  });
});

describe("without configuration", () => {
  it("reports that sign-in is unavailable rather than throwing", async () => {
    // The test environment sets no Supabase variables, so this is the
    // unconfigured build the App warns about.
    expect(isAuthConfigured).toBe(false);
    await expect(currentAccessToken()).resolves.toBeNull();
  });

  it("reports no session to a subscriber", () => {
    const listener = vi.fn();

    const unsubscribe = onSessionChange(listener);

    expect(listener).toHaveBeenCalledExactlyOnceWith(null);
    unsubscribe();
  });
});
