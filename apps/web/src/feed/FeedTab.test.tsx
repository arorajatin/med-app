import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { FeedItem, ReportExtraction } from "../api/feed";
import * as feedApi from "../api/feed";
import { AppShell } from "../navigation/AppShell";
import { mockApi, SELF_PROFILE } from "../test/apiMock";
import { mockUploadTransport, UPLOAD_RESULT } from "../test/uploadMock";
import { FeedTab } from "./FeedTab";

const ITEM: FeedItem = {
  id: "ingestion_1",
  record_id: null,
  profile: null,
  display_filename: "report.pdf",
  source_channel: "direct_file",
  source_label: "File upload",
  completed_at: "2026-09-07T10:00:00Z",
  report_date: null,
  assignment_state: "provisional",
  extraction_state: "queued",
  review_state: "not_required",
  metadata_review_pending: false,
  attention_required: false,
};

function extraction(
  overrides: Partial<ReportExtraction> = {},
): ReportExtraction {
  return {
    ingestion: {
      ...UPLOAD_RESULT.ingestion,
      assignment_state: "needs_assignment",
      extraction_state: "ready",
    },
    record: null,
    jobs: [],
    attempts: [],
    patient_evidence: [],
    metadata_candidates: [],
    observations: [],
    memory_candidates: [],
    source_references: [],
    assignment_history: [],
    ...overrides,
  };
}

/** Drive AppShell from the Upload tab up to the point the receipt arrives. */
async function uploadFromShell() {
  const xhrs = mockUploadTransport();
  render(
    <AppShell
      profile={null}
      email={null}
      onSignOut={vi.fn()}
      onUnauthenticated={vi.fn()}
    />,
  );
  await screen.findByRole("option", { name: "Asha (self)" });
  await userEvent.selectOptions(
    screen.getByLabelText("Family view"),
    SELF_PROFILE.id,
  );
  await userEvent.click(screen.getByRole("tab", { name: "Upload" }));
  await waitFor(() =>
    expect(screen.getByRole("combobox")).toHaveValue(SELF_PROFILE.id),
  );
  await userEvent.upload(
    screen.getByLabelText("Report files"),
    new File(["%PDF"], "report.pdf", { type: "application/pdf" }),
  );
  await userEvent.click(screen.getByRole("button", { name: "Upload report" }));
  await waitFor(() => expect(xhrs).toHaveLength(1));
  return xhrs;
}

function showFeed(onUnauthenticated = vi.fn()) {
  return render(
    <FeedTab
      onOpenUpload={vi.fn()}
      onUnauthenticated={onUnauthenticated}
      uploadedId={null}
    />,
  );
}

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("Feed", () => {
  it("filters by family member and resets pages while preserving the date order", async () => {
    const father = {
      ...SELF_PROFILE,
      id: "father",
      display_name: "Ravi",
      relationship: "father",
    };
    const assigned = {
      ...ITEM,
      profile: SELF_PROFILE,
      assignment_state: "resolved" as const,
    };
    const { calls } = mockApi({
      "GET /profiles": [SELF_PROFILE, father],
      "GET /feed?order=upload_date&limit=20": {
        items: [ITEM],
        next_cursor: null,
      },
      "GET /feed?order=report_date&limit=20": {
        items: [ITEM],
        next_cursor: null,
      },
      "GET /feed?order=report_date&limit=20&profile_id=profile_1": {
        items: [assigned],
        next_cursor: "more",
      },
      "GET /feed?order=report_date&limit=40&profile_id=profile_1": {
        items: [
          assigned,
          { ...assigned, id: "older", display_filename: "Older report" },
        ],
        next_cursor: null,
      },
      "GET /feed?order=report_date&limit=20&profile_id=father": {
        items: [],
        next_cursor: null,
      },
    });
    showFeed();
    const family = await screen.findByLabelText("Family view");
    expect(family).toHaveValue("");
    await screen.findByRole("option", { name: "Ravi (father)" });
    await userEvent.selectOptions(
      screen.getByLabelText("Order by"),
      "report_date",
    );
    await userEvent.selectOptions(family, SELF_PROFILE.id);
    await userEvent.click(
      await screen.findByRole("button", { name: "Load more reports" }),
    );
    expect(
      await screen.findByRole("button", { name: "Older report" }),
    ).toBeInTheDocument();
    await userEvent.selectOptions(family, father.id);
    expect(
      await screen.findByRole("heading", { name: "No reports for Ravi" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Older report" }),
    ).not.toBeInTheDocument();
    expect(screen.getByLabelText("Order by")).toHaveValue("report_date");
    expect(calls.at(-1)?.path).toBe(
      "/feed?order=report_date&limit=20&profile_id=father",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "View All Family" }),
    );
    expect(family).toHaveValue("");
    expect(
      await screen.findByText("Queued for extraction"),
    ).toBeInTheDocument();
    expect(calls.at(-1)?.path).toBe("/feed?order=report_date&limit=20");
  });

  it("ignores an old family view response after switching members", async () => {
    mockApi({ "GET /profiles": [SELF_PROFILE] });
    let finishOldRead: () => void = () => {};
    vi.spyOn(feedApi, "listFeed")
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            finishOldRead = () => resolve({ items: [ITEM], next_cursor: null });
          }),
      )
      .mockResolvedValue({ items: [], next_cursor: null });
    showFeed();
    await screen.findByRole("option", { name: "Asha (self)" });
    await userEvent.selectOptions(
      screen.getByLabelText("Family view"),
      SELF_PROFILE.id,
    );
    expect(
      await screen.findByRole("heading", { name: "No reports for Asha" }),
    ).toBeInTheDocument();
    await act(async () => finishOldRead());
    expect(
      screen.queryByRole("button", { name: "report.pdf" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "No reports for Asha" }),
    ).toBeInTheDocument();
  });

  it("keeps All Family available when member loading fails and supports retry", async () => {
    let status = 503;
    mockApi({
      "GET /profiles": () => ({
        status,
        body: status === 200 ? [SELF_PROFILE] : { detail: "Unavailable" },
      }),
      "GET /feed?order=upload_date&limit=20": {
        items: [ITEM],
        next_cursor: null,
      },
    });
    showFeed();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "All Family is still available",
    );
    expect(
      await screen.findByRole("button", { name: "report.pdf" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Family view")).toBeDisabled();
    status = 200;
    await userEvent.click(
      screen.getByRole("button", { name: "Retry family members" }),
    );
    await screen.findByRole("option", { name: "Asha (self)" });
    expect(screen.getByLabelText("Family view")).toBeEnabled();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("handles rejected credentials while loading family members", async () => {
    mockApi({
      "GET /profiles": () => ({
        status: 401,
        body: { detail: "Expired session" },
      }),
      "GET /feed?order=upload_date&limit=20": { items: [], next_cursor: null },
    });
    const signOut = vi.fn();
    showFeed(signOut);
    await waitFor(() => expect(signOut).toHaveBeenCalledOnce());
  });

  it("shows an empty state with upload access", async () => {
    mockApi({
      "GET /profiles": [SELF_PROFILE],
      "GET /feed?order=upload_date&limit=20": { items: [], next_cursor: null },
    });
    const onOpenUpload = vi.fn();
    render(
      <FeedTab
        onOpenUpload={onOpenUpload}
        onUnauthenticated={vi.fn()}
        uploadedId={null}
      />,
    );
    await userEvent.click(
      await screen.findByRole("button", { name: "Upload your first report" }),
    );
    expect(onOpenUpload).toHaveBeenCalledOnce();
  });

  it("shows independent status and source labels across family profiles", async () => {
    mockApi({
      "GET /profiles": [SELF_PROFILE],
      "GET /feed?order=upload_date&limit=20": {
        items: [
          ITEM,
          {
            ...ITEM,
            id: "camera",
            display_filename: "scan.png",
            source_channel: "camera",
            source_label: "Camera capture",
            assignment_state: "needs_assignment",
            extraction_state: "failed",
          },
          {
            ...ITEM,
            id: "resolved",
            display_filename: "Asha report.pdf",
            profile: SELF_PROFILE,
            assignment_state: "resolved",
            extraction_state: "ready",
            review_state: "reviewed",
            metadata_review_pending: true,
          },
        ],
        next_cursor: null,
      },
    });
    showFeed();
    expect(
      await screen.findByText("Queued for extraction"),
    ).toBeInTheDocument();
    expect(screen.getByText("Extraction failed")).toBeInTheDocument();
    expect(screen.getByText("Camera capture")).toBeInTheDocument();
    expect(screen.getByText("Asha")).toBeInTheDocument();
    expect(screen.getByText("Medical review complete")).toBeInTheDocument();
    expect(screen.getByText("Report details need review")).toBeInTheDocument();
    expect(
      screen.queryByText("No medical review needed"),
    ).not.toBeInTheDocument();
  });

  it("loads another page and resets pagination when ordering changes", async () => {
    const { calls } = mockApi({
      "GET /profiles": [SELF_PROFILE],
      "GET /feed?order=upload_date&limit=20": {
        items: [ITEM],
        next_cursor: "next",
      },
      "GET /feed?order=upload_date&limit=40": {
        items: [ITEM, { ...ITEM, id: "older", display_filename: "Older report" }],
        next_cursor: null,
      },
      "GET /feed?order=report_date&limit=20": {
        items: [
          {
            ...ITEM,
            id: "dated",
            display_filename: "Dated report",
            report_date: "2026-08-15",
          },
        ],
        next_cursor: null,
      },
    });
    showFeed();
    await userEvent.click(
      await screen.findByRole("button", { name: "Load more reports" }),
    );
    expect(
      await screen.findByRole("button", { name: "Older report" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "report.pdf" }),
    ).toBeInTheDocument();
    await userEvent.selectOptions(
      screen.getByLabelText("Order by"),
      "report_date",
    );
    expect(
      await screen.findByRole("button", { name: "Dated report" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Older report" }),
    ).not.toBeInTheDocument();
    expect(calls.at(-1)?.path).toBe("/feed?order=report_date&limit=20");
  });

  it("refreshes processing state and stops polling when unmounted", async () => {
    vi.useFakeTimers();
    let current = ITEM;
    const { calls } = mockApi({
      "GET /profiles": [SELF_PROFILE],
      "GET /feed?order=upload_date&limit=20": () => ({
        body: { items: [current], next_cursor: null },
      }),
    });
    const { unmount } = showFeed();
    await act(() => vi.advanceTimersByTimeAsync(0));
    expect(screen.getByText("Queued for extraction")).toBeInTheDocument();
    current = {
      ...ITEM,
      assignment_state: "needs_assignment",
      extraction_state: "ready",
    };
    await act(() => vi.advanceTimersByTimeAsync(5000));
    expect(screen.getByText("Extraction complete")).toBeInTheDocument();
    expect(screen.queryByText("Queued for extraction")).not.toBeInTheDocument();
    unmount();
    const count = calls.length;
    await act(() => vi.advanceTimersByTimeAsync(15000));
    expect(calls).toHaveLength(count);
  });

  it("recovers from a Feed error and signs out on rejected credentials", async () => {
    let status = 503;
    mockApi({
      "GET /profiles": [SELF_PROFILE],
      "GET /feed?order=upload_date&limit=20": () => ({
        status,
        body:
          status === 200
            ? { items: [ITEM], next_cursor: null }
            : { detail: "Please retry" },
      }),
    });
    const signOut = vi.fn();
    showFeed(signOut);
    expect(await screen.findByRole("alert")).toHaveTextContent("Please retry");
    status = 200;
    await userEvent.click(screen.getByRole("button", { name: "Refresh" }));
    expect(
      await screen.findByText("Queued for extraction"),
    ).toBeInTheDocument();
    status = 401;
    await userEvent.click(screen.getByRole("button", { name: "Refresh" }));
    await waitFor(() => expect(signOut).toHaveBeenCalledOnce());
  });

  it("opens processing details and allows explicit pending assignment", async () => {
    let assigned = false;
    const record = {
      id: "record_1",
      profile_id: SELF_PROFILE.id,
      ingestion_id: ITEM.id,
      display_filename: ITEM.display_filename,
      record_date: null,
      record_type: null,
      issuer_name: null,
      created_at: ITEM.completed_at,
      updated_at: ITEM.completed_at,
    };
    const { calls } = mockApi({
      "GET /profiles": [SELF_PROFILE],
      "GET /feed?order=upload_date&limit=20": {
        items: [
          {
            ...ITEM,
            assignment_state: "needs_assignment",
            extraction_state: "ready",
          },
        ],
        next_cursor: null,
      },
      "GET /ingestions/ingestion_1/extraction": () => ({
        body: assigned
          ? extraction({
              ingestion: {
                ...UPLOAD_RESULT.ingestion,
                assignment_state: "resolved",
                resolved_profile_id: SELF_PROFILE.id,
                extraction_state: "ready",
              },
              record,
            })
          : extraction(),
      }),
      "POST /ingestions/ingestion_1/assignment/profile_1": () => {
        assigned = true;
        return { body: record };
      },
    });
    showFeed();
    await userEvent.click(
      await screen.findByRole("button", { name: "Open report.pdf" }),
    );
    const select = await screen.findByLabelText("Family member");
    expect(select).toHaveValue("");
    expect(
      screen.getByRole("button", { name: "Assign report" }),
    ).toBeDisabled();
    expect(
      screen.getByText("No patient name was extracted from this report."),
    ).toBeInTheDocument();
    await userEvent.selectOptions(select, SELF_PROFILE.id);
    await userEvent.click(
      screen.getByRole("button", { name: "Assign report" }),
    );
    expect(
      await screen.findByText("Family member assigned."),
    ).toBeInTheDocument();
    expect(screen.getByText("Asha")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Assign report" }),
    ).not.toBeInTheDocument();
    expect(calls.filter((call) => call.method === "POST")).toHaveLength(1);
  });

  it("keeps an assignment error actionable without claiming success", async () => {
    mockApi({
      "GET /profiles": [SELF_PROFILE],
      "GET /feed?order=upload_date&limit=20": { items: [ITEM], next_cursor: null },
      "GET /ingestions/ingestion_1/extraction": extraction(),
      "POST /ingestions/ingestion_1/assignment/profile_1": () => ({
        status: 409,
        body: { detail: "This report is already assigned." },
      }),
    });
    showFeed();
    await userEvent.click(
      await screen.findByRole("button", { name: "Open report.pdf" }),
    );
    await userEvent.selectOptions(
      await screen.findByLabelText("Family member"),
      SELF_PROFILE.id,
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Assign report" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "already assigned",
    );
    expect(
      screen.queryByText("Family member assigned."),
    ).not.toBeInTheDocument();
  });

  it("does not show assignment controls before successful extraction", async () => {
    mockApi({
      "GET /profiles": [SELF_PROFILE],
      "GET /feed?order=upload_date&limit=20": { items: [ITEM], next_cursor: null },
      "GET /ingestions/ingestion_1/extraction": extraction({
        ingestion: UPLOAD_RESULT.ingestion,
      }),
    });
    showFeed();
    await userEvent.click(
      await screen.findByRole("button", { name: "Open report.pdf" }),
    );
    expect(
      await screen.findByText(/Processing continues here/),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Family member")).not.toBeInTheDocument();
  });

  it.each(["extraction_failed", "invalid_source_reference"])(
    "offers retry only for a retryable failure (%s)",
    async (failureCode) => {
      let retried = false;
      const { calls } = mockApi({
        "GET /profiles": [SELF_PROFILE],
        "GET /feed?order=upload_date&limit=20": {
          items: [{ ...ITEM, extraction_state: "failed" }],
          next_cursor: null,
        },
        "GET /ingestions/ingestion_1/extraction": () => ({
          body: retried
            ? extraction()
            : extraction({
                ingestion: {
                  ...UPLOAD_RESULT.ingestion,
                  extraction_state: "failed",
                },
                jobs: [
                  {
                    ...UPLOAD_RESULT.extraction_job!,
                    status: "failed",
                    failure_code: failureCode,
                  },
                ],
              }),
        }),
        "POST /extraction/jobs/job_1/retry": () => {
          retried = true;
          return {
            body: { ...UPLOAD_RESULT.extraction_job!, status: "ready" },
          };
        },
      });
      showFeed();
      await userEvent.click(
        await screen.findByRole("button", { name: "Open report.pdf" }),
      );
      await screen.findByText(/its information could not be extracted/);
      if (failureCode === "extraction_failed") {
        await userEvent.click(
          screen.getByRole("button", { name: "Retry extraction" }),
        );
        expect(
          await screen.findByText(/Extraction retry requested/),
        ).toBeInTheDocument();
        expect(screen.getByText("Extraction complete")).toBeInTheDocument();
        expect(calls.filter((call) => call.method === "POST")).toHaveLength(1);
      } else
        expect(
          screen.queryByRole("button", { name: "Retry extraction" }),
        ).not.toBeInTheDocument();
    },
  );

  it("does not let a late background read undo a saved assignment", async () => {
    mockApi({
      "GET /profiles": [SELF_PROFILE],
      "GET /feed?order=upload_date&limit=20": { items: [ITEM], next_cursor: null },
    });
    let finishAssignment: () => void = () => {};
    let finishOldRead: () => void = () => {};
    const resolved = extraction({
      ingestion: {
        ...UPLOAD_RESULT.ingestion,
        assignment_state: "resolved",
        resolved_profile_id: SELF_PROFILE.id,
        extraction_state: "ready",
      },
    });
    vi.spyOn(feedApi, "getReport")
      .mockResolvedValueOnce(extraction())
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            finishOldRead = () => resolve(extraction());
          }),
      )
      .mockResolvedValue(resolved);
    vi.spyOn(feedApi, "assignReport").mockImplementation(
      () =>
        new Promise((resolve) => {
          finishAssignment = () =>
            resolve({
              id: "record_1",
              profile_id: SELF_PROFILE.id,
              ingestion_id: ITEM.id,
              display_filename: ITEM.display_filename,
              record_date: null,
              record_type: null,
              issuer_name: null,
              created_at: ITEM.completed_at,
              updated_at: ITEM.completed_at,
            });
        }),
    );
    vi.useFakeTimers();
    showFeed();
    await act(() => vi.advanceTimersByTimeAsync(0));
    fireEvent.click(screen.getByRole("button", { name: "Open report.pdf" }));
    await act(() => vi.advanceTimersByTimeAsync(0));
    fireEvent.change(screen.getByLabelText("Family member"), { target: { value: SELF_PROFILE.id } });
    fireEvent.click(screen.getByRole("button", { name: "Assign report" }));
    await act(() => vi.advanceTimersByTimeAsync(5000));
    await act(async () => finishAssignment());
    expect(screen.getByText("Family member assigned.")).toBeInTheDocument();
    await act(async () => finishOldRead());
    expect(screen.getByText("Asha")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Assign report" }),
    ).not.toBeInTheDocument();
  });

  it("opens Feed and highlights the report only after the upload receipt", async () => {
    let complete = false;
    mockApi({
      "GET /profiles": [SELF_PROFILE],
      "GET /feed?order=upload_date&limit=20&profile_id=profile_1": {
        items: [], next_cursor: null,
      },
      "GET /feed?order=upload_date&limit=20": () => ({
        body: { items: complete ? [ITEM] : [], next_cursor: null },
      }),
    });
    const xhrs = await uploadFromShell();
    act(() => xhrs[0]!.progress(100));
    expect(screen.getByRole("tab", { name: "Upload" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    complete = true;
    await act(async () => xhrs[0]!.respond());
    expect(screen.getByRole("tab", { name: "Feed" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    const reports = screen.getByRole("list", { name: "Reports" });
    expect(screen.getByLabelText("Family view")).toHaveValue("");
    expect(
      await within(reports).findByText("Just uploaded · saved privately"),
    ).toBeInTheDocument();
    expect(
      within(reports).getByRole("button", { name: "report.pdf" }),
    ).toHaveFocus();
  });

  it("returns to a fresh Upload form after handing off to Feed", async () => {
    mockApi({
      "GET /profiles": [SELF_PROFILE],
      "GET /feed?order=upload_date&limit=20&profile_id=profile_1": {
        items: [], next_cursor: null,
      },
      "GET /feed?order=upload_date&limit=20": { items: [ITEM], next_cursor: null },
    });
    const xhrs = await uploadFromShell();
    await act(async () => xhrs[0]!.respond());
    await userEvent.click(screen.getByRole("tab", { name: "Upload" }));
    expect(
      await screen.findByRole("heading", { name: "Upload a report" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Report uploaded")).not.toBeInTheDocument();
  });

  it("stays on the current tab when an upload finishes in the background", async () => {
    mockApi({
      "GET /profiles": [SELF_PROFILE],
      "GET /feed?order=upload_date&limit=20&profile_id=profile_1": {
        items: [], next_cursor: null,
      },
      "GET /feed?order=upload_date&limit=20": { items: [ITEM], next_cursor: null },
    });
    const xhrs = await uploadFromShell();
    await userEvent.click(screen.getByRole("tab", { name: "Drive" }));
    await act(async () => xhrs[0]!.respond());
    expect(screen.getByRole("tab", { name: "Drive" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await userEvent.click(screen.getByRole("tab", { name: "Upload" }));
    expect(await screen.findByText("Report uploaded")).toBeInTheDocument();
  });

  it("keeps an open report when an upload finishes in the background", async () => {
    mockApi({
      "GET /profiles": [SELF_PROFILE],
      "GET /feed?order=upload_date&limit=20&profile_id=profile_1": {
        items: [ITEM], next_cursor: null,
      },
      "GET /feed?order=upload_date&limit=20": { items: [ITEM], next_cursor: null },
      "GET /ingestions/ingestion_1/extraction": extraction(),
    });
    const xhrs = await uploadFromShell();
    await userEvent.click(screen.getByRole("tab", { name: "Feed" }));
    await userEvent.click(
      await screen.findByRole("button", { name: "Open report.pdf" }),
    );
    await screen.findByRole("button", { name: "← Back to Feed" });
    await act(async () => xhrs[0]!.respond());
    expect(
      screen.getByRole("button", { name: "← Back to Feed" }),
    ).toBeInTheDocument();
  });

  it("asks for an assignment only once the patient match has settled", async () => {
    mockApi({
      "GET /profiles": [SELF_PROFILE],
      "GET /feed?order=upload_date&limit=20": {
        items: [
          { ...ITEM, display_filename: "pending.pdf" },
          {
            ...ITEM,
            id: "ingestion_2",
            display_filename: "unassigned.pdf",
            assignment_state: "needs_assignment",
            extraction_state: "ready",
            attention_required: true,
          },
        ],
        next_cursor: null,
      },
    });
    showFeed();
    const pending = (
      await screen.findByRole("button", { name: "pending.pdf" })
    ).closest("li")!;
    expect(
      within(pending).getByText("Checking patient details"),
    ).toBeInTheDocument();
    expect(
      within(pending).getByText("Patient match pending"),
    ).toBeInTheDocument();
    expect(
      within(pending).queryByText("Needs assignment"),
    ).not.toBeInTheDocument();
    const unassigned = screen
      .getByRole("button", { name: "unassigned.pdf" })
      .closest("li")!;
    expect(within(unassigned).getAllByText("Needs assignment")).toHaveLength(2);
  });

  it("polls every loaded page in a single request", async () => {
    vi.useFakeTimers();
    const { calls } = mockApi({
      "GET /profiles": [SELF_PROFILE],
      "GET /feed?order=upload_date&limit=20": {
        items: [ITEM],
        next_cursor: "next",
      },
      "GET /feed?order=upload_date&limit=40": {
        items: [ITEM, { ...ITEM, id: "older", display_filename: "Older report" }],
        next_cursor: null,
      },
    });
    showFeed();
    await act(() => vi.advanceTimersByTimeAsync(0));
    fireEvent.click(screen.getByRole("button", { name: "Load more reports" }));
    await act(() => vi.advanceTimersByTimeAsync(0));
    const settled = calls.length;
    await act(() => vi.advanceTimersByTimeAsync(5000));
    expect(calls.slice(settled).map((call) => call.path)).toEqual([
      "/feed?order=upload_date&limit=40",
    ]);
  });
});
