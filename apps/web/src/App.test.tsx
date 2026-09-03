import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import type { AccountSession } from "./auth/session";
import { mockApi, onboardingState } from "./test/apiMock";

const signInWithGoogle = vi.fn<() => Promise<void>>();
const signOut = vi.fn<() => Promise<void>>();
const readAuthRedirectError = vi.fn<() => string | null>();
const clearAuthRedirectError = vi.fn<() => void>();

/** Drives the session the App sees, standing in for the Supabase client. */
let sessionListener: ((session: AccountSession | null) => void) | null = null;
let currentSession: AccountSession | null = null;
let authConfigured = true;

vi.mock("./auth/session", () => ({
  get isAuthConfigured() {
    return authConfigured;
  },
  currentAccessToken: async () => "test-access-token",
  onSessionChange: (listener: (session: AccountSession | null) => void) => {
    sessionListener = listener;
    listener(currentSession);
    return () => {
      sessionListener = null;
    };
  },
  signInWithGoogle: () => signInWithGoogle(),
  signOut: () => {
    currentSession = null;
    sessionListener?.(null);
    return signOut();
  },
  readAuthRedirectError: () => readAuthRedirectError(),
  clearAuthRedirectError: () => clearAuthRedirectError(),
}));

const SIGNED_IN: AccountSession = { userId: "user_1", email: "asha@example.com" };

beforeEach(() => {
  currentSession = null;
  sessionListener = null;
  authConfigured = true;
  readAuthRedirectError.mockReturnValue(null);
  signInWithGoogle.mockResolvedValue(undefined);
  signOut.mockResolvedValue(undefined);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe("App", () => {
  it("offers Google as the only way in", async () => {
    mockApi({});

    render(<App />);

    expect(await screen.findByRole("button", { name: /Continue with Google/ })).toBeInTheDocument();
    expect(screen.queryByLabelText(/token/i)).not.toBeInTheDocument();
  });

  it("hands off to Google when the person chooses it", async () => {
    mockApi({});
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: /Continue with Google/ }));

    expect(signInWithGoogle).toHaveBeenCalledOnce();
  });

  it("reports a sign-in that could not be started", async () => {
    signInWithGoogle.mockRejectedValue(new Error("Provider google is not enabled."));
    mockApi({});
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: /Continue with Google/ }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Provider google is not enabled.");
  });

  it("shows a failure carried back on the redirect and clears it from the URL", async () => {
    readAuthRedirectError.mockReturnValue("The user denied access.");
    mockApi({});

    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent("The user denied access.");
    expect(clearAuthRedirectError).toHaveBeenCalledOnce();
  });

  it("opens onboarding for a restored session and shows who is signed in", async () => {
    currentSession = SIGNED_IN;
    mockApi({ "GET /account/onboarding": onboardingState({ status: "not_started" }) });

    render(<App />);

    expect(await screen.findByRole("heading", { name: "AI processing terms" })).toBeInTheDocument();
    expect(screen.getByText("asha@example.com")).toBeInTheDocument();
  });

  it("returns to the sign-in screen after signing out", async () => {
    currentSession = SIGNED_IN;
    mockApi({ "GET /account/onboarding": onboardingState({ status: "not_started" }) });

    render(<App />);
    await screen.findByRole("heading", { name: "AI processing terms" });
    await userEvent.click(screen.getByRole("button", { name: "Sign out" }));

    expect(signOut).toHaveBeenCalledOnce();
    expect(await screen.findByRole("button", { name: /Continue with Google/ })).toBeInTheDocument();
  });

  it("explains an unconfigured build instead of offering a broken button", async () => {
    authConfigured = false;
    mockApi({});

    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Sign-in is not configured");
    expect(screen.queryByRole("button", { name: /Continue with Google/ })).not.toBeInTheDocument();
  });
});
