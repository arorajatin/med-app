import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { mockApi, onboardingState } from "./test/apiMock";

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("asks for a token, then keeps the session for the next visit", async () => {
    const { calls } = mockApi({
      "GET /account": { id: "account_1", onboarding_status: "not_started" },
      "GET /account/onboarding": onboardingState({ status: "not_started" }),
    });

    render(<App />);

    await userEvent.type(screen.getByLabelText("User id or access token"), "user_1");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(await screen.findByRole("heading", { name: "AI processing terms" })).toBeInTheDocument();
    expect(window.localStorage.getItem("med-app.session-token")).toBe("user_1");
    expect(calls[0]).toMatchObject({ method: "GET", path: "/account" });
  });

  it("keeps the person on the sign-in screen when the API rejects the token", async () => {
    mockApi({
      "GET /account": () => ({ status: 401, body: { detail: "Missing local auth user." } }),
    });

    render(<App />);

    await userEvent.type(screen.getByLabelText("User id or access token"), "nobody");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Missing local auth user.");
    expect(window.localStorage.getItem("med-app.session-token")).toBeNull();
  });

  it("signs out and clears the stored session", async () => {
    window.localStorage.setItem("med-app.session-token", "user_1");
    mockApi({
      "GET /account/onboarding": onboardingState({ status: "not_started" }),
    });

    render(<App />);

    await screen.findByRole("heading", { name: "AI processing terms" });
    await userEvent.click(screen.getByRole("button", { name: "Sign out" }));

    expect(screen.getByLabelText("User id or access token")).toBeInTheDocument();
    expect(window.localStorage.getItem("med-app.session-token")).toBeNull();
  });
});
