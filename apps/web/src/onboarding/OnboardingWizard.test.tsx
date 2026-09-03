import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { OnboardingWizard } from "./OnboardingWizard";
import { SELF_PROFILE, mockApi, onboardingState } from "../test/apiMock";

afterEach(() => {
  vi.unstubAllGlobals();
});

function renderWizard(onUnauthenticated = vi.fn()) {
  render(<OnboardingWizard token="user_1" onUnauthenticated={onUnauthenticated} />);
  return onUnauthenticated;
}

describe("OnboardingWizard", () => {
  it("resumes at the first step the account has not finished", async () => {
    mockApi({
      "GET /account/onboarding": onboardingState({
        next_step: "health_context",
        completed_steps: ["consent", "self_profile"],
        self_profile: SELF_PROFILE,
      }),
    });

    renderWizard();

    expect(await screen.findByRole("heading", { name: "Age and weight" })).toBeInTheDocument();
    const steps = within(screen.getByRole("navigation", { name: "Onboarding steps" })).getAllByRole(
      "listitem",
    );
    expect(steps[0]).toHaveTextContent("Done");
    expect(steps[2]).toHaveTextContent("In progress");
  });

  it("moves to the next step once consent is accepted", async () => {
    let accepted = false;
    const { calls } = mockApi({
      "GET /account/onboarding": () =>
        accepted
          ? { body: onboardingState({ next_step: "self_profile", completed_steps: ["consent"] }) }
          : { body: onboardingState({ status: "not_started" }) },
      "POST /account/consents": () => {
        accepted = true;
        return {
          status: 201,
          body: {
            id: "consent_1",
            policy_version: "2026-07-01",
            accepted_scope: { ai_processing: true },
            accepted_at: "2026-07-01T00:00:00Z",
          },
        };
      },
    });

    renderWizard();

    await screen.findByRole("heading", { name: "AI processing terms" });
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: "Accept and continue" }));

    expect(await screen.findByRole("heading", { name: "Your name" })).toBeInTheDocument();
    const consentCall = calls.find((call) => call.path === "/account/consents");
    expect(consentCall?.body).toMatchObject({
      policy_version: "2026-07-01",
      accepted_scope: { ai_processing: true },
    });
  });

  it("blocks acceptance until the terms box is ticked", async () => {
    const { calls } = mockApi({ "GET /account/onboarding": onboardingState() });

    renderWizard();

    await screen.findByRole("heading", { name: "AI processing terms" });
    await userEvent.click(screen.getByRole("button", { name: "Accept and continue" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Tick the box");
    expect(calls.some((call) => call.path === "/account/consents")).toBe(false);
  });

  it("keeps an invalid age on the step and sends nothing", async () => {
    const { calls } = mockApi({
      "GET /account/onboarding": onboardingState({
        next_step: "health_context",
        completed_steps: ["consent", "self_profile"],
        self_profile: SELF_PROFILE,
      }),
    });

    renderWizard();

    await screen.findByRole("heading", { name: "Age and weight" });
    await userEvent.type(screen.getByLabelText("Age in years"), "34.5");
    await userEvent.type(screen.getByLabelText("Weight"), "61.5");
    await userEvent.click(screen.getByRole("button", { name: "Save and continue" }));

    expect(
      await screen.findByText("Enter age as whole completed years, without decimals."),
    ).toBeInTheDocument();
    expect(calls.some((call) => call.path.endsWith("/health-context"))).toBe(false);
  });

  it("sends age and weight with the reported time and the entered unit", async () => {
    let recorded = false;
    const { calls } = mockApi({
      "GET /account/onboarding": () => ({
        body: onboardingState({
          next_step: recorded ? "conditions" : "health_context",
          completed_steps: recorded
            ? ["consent", "self_profile", "health_context"]
            : ["consent", "self_profile"],
          self_profile: SELF_PROFILE,
        }),
      }),
      "POST /profiles/profile_1/health-context": () => {
        recorded = true;
        return { status: 201, body: { id: "hc_1", profile_id: SELF_PROFILE.id } };
      },
      "GET /profiles/profile_1/memory": { profile: SELF_PROFILE, facts: [] },
    });

    renderWizard();

    await screen.findByRole("heading", { name: "Age and weight" });
    await userEvent.type(screen.getByLabelText("Age in years"), "34");
    await userEvent.type(screen.getByLabelText("Weight"), "150");
    await userEvent.selectOptions(screen.getByLabelText("Weight unit"), "lb");
    await userEvent.click(screen.getByRole("button", { name: "Save and continue" }));

    await screen.findByRole("heading", { name: "Current conditions" });
    const call = calls.find((entry) => entry.path.endsWith("/health-context"));
    const body = call?.body as Record<string, unknown>;
    expect(body.reported_age).toBe(34);
    expect(body.entered_weight).toBe("150");
    expect(body.weight_unit).toBe("lb");
    expect(body.age_reported_at).toBe(body.weight_reported_at);
    expect(typeof body.age_reported_at).toBe("string");
  });

  it("prefills declared conditions and replaces them with the submitted set", async () => {
    const { calls } = mockApi({
      "GET /account/onboarding": onboardingState({
        next_step: "conditions",
        completed_steps: ["consent", "self_profile", "health_context"],
        self_profile: SELF_PROFILE,
      }),
      "GET /profiles/profile_1/memory": {
        profile: SELF_PROFILE,
        facts: [
          {
            id: "fact_1",
            profile_id: SELF_PROFILE.id,
            provenance: "user_attested",
            category: "condition",
            title: "Asthma",
            details: {},
            is_active: true,
            created_at: "2026-07-01T00:00:00Z",
          },
          {
            id: "fact_2",
            profile_id: SELF_PROFILE.id,
            provenance: "user_attested",
            category: "medication",
            title: "Salbutamol",
            details: {},
            is_active: true,
            created_at: "2026-07-01T00:00:00Z",
          },
        ],
      },
      "PUT /profiles/profile_1/attested-conditions": {
        category: "condition",
        declared_at: "2026-07-02T00:00:00Z",
        facts: [],
      },
    });

    renderWizard();

    const firstEntry = await screen.findByDisplayValue("Asthma");
    expect(screen.queryByDisplayValue("Salbutamol")).not.toBeInTheDocument();

    await userEvent.clear(firstEntry);
    await userEvent.type(firstEntry, "Seasonal asthma");
    await userEvent.click(screen.getByRole("button", { name: "Save and continue" }));

    await waitFor(() => {
      const call = calls.find((entry) => entry.path.endsWith("/attested-conditions"));
      expect(call?.body).toEqual({ entries: [{ title: "Seasonal asthma", details: {} }] });
    });
  });

  it("records an explicit none answer for medications", async () => {
    const { calls } = mockApi({
      "GET /account/onboarding": onboardingState({
        next_step: "medications",
        completed_steps: ["consent", "self_profile", "health_context", "conditions"],
        self_profile: SELF_PROFILE,
      }),
      "GET /profiles/profile_1/memory": { profile: SELF_PROFILE, facts: [] },
      "PUT /profiles/profile_1/attested-medications": {
        category: "medication",
        declared_at: "2026-07-02T00:00:00Z",
        facts: [],
      },
    });

    renderWizard();

    await screen.findByRole("heading", { name: "Current medications" });
    await userEvent.click(screen.getByRole("checkbox", { name: /no medications/i }));
    await userEvent.click(screen.getByRole("button", { name: "Save and continue" }));

    await waitFor(() => {
      const call = calls.find((entry) => entry.path.endsWith("/attested-medications"));
      expect(call?.body).toEqual({ entries: [] });
    });
  });

  it("shows the summary when every step is complete", async () => {
    mockApi({
      "GET /account/onboarding": onboardingState({
        status: "completed",
        next_step: null,
        completed_steps: ["consent", "self_profile", "health_context", "conditions", "medications"],
        self_profile: SELF_PROFILE,
      }),
      "GET /profiles/profile_1/memory": { profile: SELF_PROFILE, facts: [] },
    });

    renderWizard();

    expect(await screen.findByRole("heading", { name: "Onboarding complete" })).toBeInTheDocument();
    expect(await screen.findByText("You reported no current conditions.")).toBeInTheDocument();
  });

  it("signs the person out when the API rejects the session", async () => {
    mockApi({
      "GET /account/onboarding": () => ({ status: 401, body: { detail: "Missing local auth user." } }),
    });

    const onUnauthenticated = renderWizard();

    await waitFor(() => expect(onUnauthenticated).toHaveBeenCalled());
  });
});
