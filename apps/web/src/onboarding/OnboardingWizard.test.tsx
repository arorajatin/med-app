import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { OnboardingWizard } from "./OnboardingWizard";
import { SELF_PROFILE, healthContextSummary, mockApi, onboardingState } from "../test/apiMock";

afterEach(() => {
  vi.unstubAllGlobals();
});

function renderWizard(onUnauthenticated = vi.fn()) {
  render(
    <OnboardingWizard
      email="asha@example.com"
      onSignOut={vi.fn()}
      onUnauthenticated={onUnauthenticated}
    />,
  );
  return onUnauthenticated;
}

describe("OnboardingWizard", () => {
  it("redirects to Upload as soon as the final onboarding step is saved", async () => {
    let complete = false;
    mockApi({
      "GET /account/onboarding": () => ({ body: onboardingState({
        status: complete ? "completed" : "in_progress",
        next_step: complete ? null : "medications",
        completed_steps: complete
          ? ["self_profile", "health_context", "conditions", "medications"]
          : ["self_profile", "health_context", "conditions"],
        self_profile: SELF_PROFILE,
      }) }),
      "GET /profiles/profile_1/health-context": healthContextSummary(),
      "GET /profiles/profile_1/memory": { profile: SELF_PROFILE, facts: [] },
      "PUT /profiles/profile_1/attested-medications": () => {
        complete = true;
        return { body: { category: "medication", facts: [] } };
      },
      "GET /profiles": [SELF_PROFILE],
    });
    renderWizard();
    await screen.findByRole("heading", { name: "Current medications" });
    expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("checkbox", { name: /no medications/i }));
    await userEvent.click(screen.getByRole("button", { name: "Save and continue" }));
    expect(await screen.findByRole("heading", { name: "Upload a report" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Upload" })).toHaveAttribute("aria-selected", "true");
  });

  it("resumes at the first step the account has not finished", async () => {
    mockApi({
      "GET /profiles/profile_1/health-context": healthContextSummary(),
      "GET /account/onboarding": onboardingState({
        next_step: "health_context",
        completed_steps: ["self_profile"],
        self_profile: SELF_PROFILE,
      }),
    });

    renderWizard();

    expect(await screen.findByRole("heading", { name: "Age and weight" })).toBeInTheDocument();
    const steps = within(screen.getByRole("navigation", { name: "Onboarding steps" })).getAllByRole(
      "listitem",
    );
    expect(steps[0]).toHaveTextContent("Done");
    expect(steps[1]).toHaveTextContent("In progress");
  });

  it("returns to the next required step after correcting an earlier answer", async () => {
    const state = onboardingState({
      next_step: "health_context",
      completed_steps: ["self_profile"],
      self_profile: SELF_PROFILE,
    });
    mockApi({
      "GET /profiles/profile_1/health-context": healthContextSummary(),
      "GET /account/onboarding": state,
      "PUT /account/onboarding/self-profile": SELF_PROFILE,
    });

    renderWizard();

    await screen.findByRole("heading", { name: "Age and weight" });
    await userEvent.click(screen.getByRole("button", { name: "Your name" }));
    await userEvent.click(screen.getByRole("button", { name: "Save and continue" }));

    expect(await screen.findByRole("heading", { name: "Age and weight" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Your health summary" })).not.toBeInTheDocument();
  });

  it("returns to the next required step when cancelling an earlier edit", async () => {
    mockApi({
      "GET /profiles/profile_1/health-context": healthContextSummary(),
      "GET /account/onboarding": onboardingState({
        next_step: "health_context",
        completed_steps: ["self_profile"],
        self_profile: SELF_PROFILE,
      }),
    });

    renderWizard();

    await screen.findByRole("heading", { name: "Age and weight" });
    await userEvent.click(screen.getByRole("button", { name: "Your name" }));
    await userEvent.click(screen.getByRole("button", { name: "Back to current step" }));

    expect(screen.getByRole("heading", { name: "Age and weight" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Your health summary" })).not.toBeInTheDocument();
  });

  it("keeps an invalid age on the step and sends nothing", async () => {
    const { calls } = mockApi({
      "GET /profiles/profile_1/health-context": healthContextSummary(),
      "GET /account/onboarding": onboardingState({
        next_step: "health_context",
        completed_steps: ["self_profile"],
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
    expect(
      calls.some((call) => call.method === "POST" && call.path.endsWith("/health-context")),
    ).toBe(false);
  });

  it("sends age and weight with the reported time and the entered unit", async () => {
    let recorded = false;
    const { calls } = mockApi({
      "GET /account/onboarding": () => ({
        body: onboardingState({
          next_step: recorded ? "conditions" : "health_context",
          completed_steps: recorded
            ? ["self_profile", "health_context"]
            : ["self_profile"],
          self_profile: SELF_PROFILE,
        }),
      }),
      "POST /profiles/profile_1/health-context": () => {
        recorded = true;
        return { status: 201, body: { id: "hc_1", profile_id: SELF_PROFILE.id } };
      },
      "GET /profiles/profile_1/health-context": () => ({ body: healthContextSummary() }),
      "GET /profiles/profile_1/memory": { profile: SELF_PROFILE, facts: [] },
    });

    renderWizard();

    await screen.findByRole("heading", { name: "Age and weight" });
    await userEvent.type(screen.getByLabelText("Age in years"), "34");
    await userEvent.type(screen.getByLabelText("Weight"), "150");
    await userEvent.selectOptions(screen.getByLabelText("Weight unit"), "lb");
    await userEvent.click(screen.getByRole("button", { name: "Save and continue" }));

    await screen.findByRole("heading", { name: "Current conditions" });
    const call = calls.find(
      (entry) => entry.method === "POST" && entry.path.endsWith("/health-context"),
    );
    const body = call?.body as Record<string, unknown>;
    expect(body.reported_age).toBe(34);
    expect(body.entered_weight).toBe("150");
    expect(body.weight_unit).toBe("lb");
    expect(body.age_reported_at).toBe(body.weight_reported_at);
    expect(typeof body.age_reported_at).toBe("string");
  });

  it("prefills declared conditions and replaces them with the submitted set", async () => {
    const { calls } = mockApi({
      "GET /profiles/profile_1/health-context": healthContextSummary(),
      "GET /account/onboarding": onboardingState({
        next_step: "conditions",
        completed_steps: ["self_profile", "health_context"],
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
      "GET /profiles/profile_1/health-context": healthContextSummary(),
      "GET /account/onboarding": onboardingState({
        next_step: "medications",
        completed_steps: ["self_profile", "health_context", "conditions"],
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

  it("shows the age and weight already on the profile when the step is revisited", async () => {
    mockApi({
      "GET /account/onboarding": onboardingState({
        next_step: "health_context",
        completed_steps: ["self_profile", "health_context"],
        self_profile: SELF_PROFILE,
      }),
      "GET /profiles/profile_1/health-context": healthContextSummary({
        age_refresh_due: true,
      }),
    });

    renderWizard();

    await screen.findByRole("heading", { name: "Age and weight" });
    expect(await screen.findByText(/34 years/)).toBeInTheDocument();
    expect(screen.getByText(/61.5 kg/)).toBeInTheDocument();
    expect(screen.getByText(/This age is worth reporting again/)).toBeInTheDocument();
    expect(screen.queryByText(/This weight is worth reporting again/)).not.toBeInTheDocument();
  });

  it("shows the recorded age and weight on the completed summary", async () => {
    mockApi({
      "GET /account/onboarding": onboardingState({
        status: "completed",
        next_step: null,
        completed_steps: ["self_profile", "health_context", "conditions", "medications"],
        self_profile: SELF_PROFILE,
      }),
      "GET /profiles/profile_1/health-context": healthContextSummary(),
      "GET /profiles/profile_1/memory": { profile: SELF_PROFILE, facts: [] },
      "GET /profiles": [SELF_PROFILE],
    });

    renderWizard();

    await userEvent.click(await screen.findByRole("tab", { name: "Profile" }));
    await screen.findByRole("heading", { name: "Your health summary" });
    // The reported date is rendered in the runtime's locale, so match around it.
    expect(await screen.findByText(/34 years · reported .*2026/)).toBeInTheDocument();
    expect(screen.getByText(/61.5 kg · reported .*2026/)).toBeInTheDocument();
  });

  it("opens Upload when every step is complete and keeps the summary under Profile", async () => {
    mockApi({
      "GET /account/onboarding": onboardingState({
        status: "completed",
        next_step: null,
        completed_steps: ["self_profile", "health_context", "conditions", "medications"],
        self_profile: SELF_PROFILE,
      }),
      "GET /profiles/profile_1/memory": { profile: SELF_PROFILE, facts: [] },
      "GET /profiles/profile_1/health-context": healthContextSummary(),
      "GET /profiles": [SELF_PROFILE],
    });

    renderWizard();

    expect(await screen.findByRole("heading", { name: "Upload a report" })).toBeInTheDocument();
    expect(screen.getAllByRole("tab").map((tab) => tab.textContent)).toEqual(["Feed", "Chat", "Upload", "Drive", "Profile"]);
    expect(screen.queryByRole("navigation", { name: "Onboarding steps" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Profile" }));
    expect(await screen.findByRole("heading", { name: "Your health summary" })).toBeInTheDocument();
    expect(await screen.findByText("You reported no current conditions.")).toBeInTheDocument();
    // Profile keeps the existing family space available.
    expect(await screen.findByRole("heading", { name: "Your family" })).toBeInTheDocument();
  });

  it("signs the person out when the API rejects the session", async () => {
    mockApi({
      "GET /account/onboarding": () => ({ status: 401, body: { detail: "Missing local auth user." } }),
    });

    const onUnauthenticated = renderWizard();

    await waitFor(() => expect(onUnauthenticated).toHaveBeenCalled());
  });

  it.each(["server", "network"])("shows a %s health-context failure instead of missing data", async (failure) => {
    mockApi({
      "GET /account/onboarding": onboardingState({
        status: "completed",
        next_step: null,
        self_profile: SELF_PROFILE,
      }),
      "GET /profiles/profile_1/health-context": () => {
        if (failure === "network") {
          throw new TypeError("Failed to fetch");
        }
        return { status: 500, body: { detail: "Could not load your health context." } };
      },
    });

    const onUnauthenticated = renderWizard();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      failure === "network" ? "Could not reach the server" : "Could not load your health context",
    );
    expect(screen.queryByText("Not recorded yet.")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Your health summary" })).not.toBeInTheDocument();
    expect(onUnauthenticated).not.toHaveBeenCalled();
  });

  it("signs out when the health-context read rejects the session", async () => {
    mockApi({
      "GET /account/onboarding": onboardingState({ self_profile: SELF_PROFILE }),
      "GET /profiles/profile_1/health-context": () => ({
        status: 401,
        body: { detail: "Your session has ended." },
      }),
    });

    const onUnauthenticated = renderWizard();

    await waitFor(() => expect(onUnauthenticated).toHaveBeenCalledOnce());
  });

  it("keeps recorded values when the health-context reload fails after saving", async () => {
    let saved = false;
    mockApi({
      "GET /account/onboarding": onboardingState({
        status: "completed",
        next_step: null,
        completed_steps: ["self_profile", "health_context", "conditions", "medications"],
        self_profile: SELF_PROFILE,
      }),
      "GET /profiles/profile_1/health-context": () => saved
        ? { status: 500, body: { detail: "Could not reload your health context." } }
        : { body: healthContextSummary() },
      "GET /profiles/profile_1/memory": { profile: SELF_PROFILE, facts: [] },
      "GET /profiles": [SELF_PROFILE],
      "PUT /account/onboarding/self-profile": () => {
        saved = true;
        return { body: SELF_PROFILE };
      },
    });

    renderWizard();

    await userEvent.click(await screen.findByRole("tab", { name: "Profile" }));
    await screen.findByRole("heading", { name: "Your health summary" });
    await userEvent.click(screen.getAllByRole("button", { name: "Change" })[0]!);
    await userEvent.click(screen.getByRole("button", { name: "Save and continue" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Could not reload your health context.");
    await userEvent.click(screen.getByRole("button", { name: "Back to summary" }));
    expect(await screen.findByText(/34 years/)).toBeInTheDocument();
    expect(screen.getByText(/61.5 kg/)).toBeInTheDocument();
    expect(screen.queryByText("Not recorded yet.")).not.toBeInTheDocument();
  });
});
