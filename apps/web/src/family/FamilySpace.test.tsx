import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FamilySpace } from "./FamilySpace";
import { SELF_PROFILE, mockApi } from "../test/apiMock";

afterEach(() => {
  vi.unstubAllGlobals();
});

const RAVI = {
  id: "profile_2",
  display_name: "Ravi",
  relationship: "father",
  sex: "male",
  created_at: "2026-07-02T00:00:00Z",
  updated_at: "2026-07-02T00:00:00Z",
};

function renderFamilySpace(onUnauthenticated = vi.fn()) {
  render(<FamilySpace onUnauthenticated={onUnauthenticated} />);
  return onUnauthenticated;
}

describe("FamilySpace", () => {
  it("lists every profile the account manages and marks your own", async () => {
    mockApi({ "GET /profiles": [SELF_PROFILE, RAVI] });

    renderFamilySpace();

    const entries = await screen.findAllByRole("listitem");
    expect(within(entries[0]!).getByText("Asha")).toBeInTheDocument();
    expect(within(entries[0]!).getByText("You")).toBeInTheDocument();
    expect(within(entries[1]!).getByText("Ravi")).toBeInTheDocument();
    expect(within(entries[1]!).getByText(/father/)).toBeInTheDocument();
  });

  it("adds a family member and re-reads the list from the service", async () => {
    let created = false;
    const { calls } = mockApi({
      "GET /profiles": () => ({ body: created ? [SELF_PROFILE, RAVI] : [SELF_PROFILE] }),
      "POST /profiles": () => {
        created = true;
        return { status: 201, body: RAVI };
      },
    });

    renderFamilySpace();

    await screen.findByText("Asha");
    await userEvent.click(screen.getByRole("button", { name: "Add a family member" }));
    await userEvent.type(screen.getByLabelText("Name"), "Ravi");
    await userEvent.type(screen.getByLabelText("Relationship to you"), "father");
    await userEvent.selectOptions(screen.getByLabelText("Sex (optional)"), "male");
    await userEvent.click(screen.getByRole("button", { name: "Add family member" }));

    expect(await screen.findByText("Ravi")).toBeInTheDocument();
    const call = calls.find((entry) => entry.method === "POST");
    expect(call?.body).toEqual({ display_name: "Ravi", relationship: "father", sex: "male" });
  });

  it("keeps an incomplete family member on the form and sends nothing", async () => {
    const { calls } = mockApi({ "GET /profiles": [SELF_PROFILE] });

    renderFamilySpace();

    await screen.findByText("Asha");
    await userEvent.click(screen.getByRole("button", { name: "Add a family member" }));
    await userEvent.type(screen.getByLabelText("Name"), "Ravi");
    await userEvent.click(screen.getByRole("button", { name: "Add family member" }));

    expect(
      await screen.findByText("Say how this person relates to you, for example mother."),
    ).toBeInTheDocument();
    expect(calls.some((entry) => entry.method === "POST")).toBe(false);
  });

  it("shows the service's own refusal, such as a second self profile", async () => {
    mockApi({
      "GET /profiles": [SELF_PROFILE],
      "POST /profiles": () => ({
        status: 409,
        body: { detail: "This account already has a self profile." },
      }),
    });

    renderFamilySpace();

    await screen.findByText("Asha");
    await userEvent.click(screen.getByRole("button", { name: "Add a family member" }));
    await userEvent.type(screen.getByLabelText("Name"), "Someone");
    await userEvent.type(screen.getByLabelText("Relationship to you"), "self");
    await userEvent.click(screen.getByRole("button", { name: "Add family member" }));

    expect(
      await screen.findByText("This account already has a self profile."),
    ).toBeInTheDocument();
  });

  it("signs out when the session is no longer valid", async () => {
    mockApi({
      "GET /profiles": () => ({ status: 401, body: { detail: "Your session has ended." } }),
    });

    const onUnauthenticated = renderFamilySpace();

    await waitFor(() => expect(onUnauthenticated).toHaveBeenCalled());
  });
});
