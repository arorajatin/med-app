import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppShell } from "../navigation/AppShell";
import { SELF_PROFILE, mockApi } from "../test/apiMock";
import { UPLOAD_RESULT, mockUploadTransport } from "../test/uploadMock";
import { UploadTab } from "./UploadTab";
import * as validation from "./validation";

const pdf = () =>
  new File(["%PDF-test"], "report.pdf", { type: "application/pdf" });
const photo = (name: string) =>
  new File(["image"], name, { type: "image/png" });

beforeEach(() => {
  vi.spyOn(validation, "validateImage").mockResolvedValue();
  vi.stubGlobal(
    "URL",
    class extends URL {
      static createObjectURL = vi.fn(() => `blob:${crypto.randomUUID()}`);
      static revokeObjectURL = vi.fn();
    },
  );
  mockApi({ "GET /profiles": [SELF_PROFILE] });
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

async function selectProfile() {
  await screen.findByRole("option", { name: "Asha · You" });
  await userEvent.selectOptions(
    screen.getByLabelText("Who is this report for?"),
    SELF_PROFILE.id,
  );
}

async function selectFiles(files: File | File[]) {
  await userEvent.upload(screen.getByLabelText("Report files"), files);
}

describe("UploadTab", () => {
  it("opens on the account's own profile as a provisional selection", async () => {
    render(<UploadTab active onUnauthenticated={vi.fn()} />);
    await screen.findByRole("option", { name: "Asha · You" });
    expect(screen.getByLabelText("Who is this report for?")).toHaveValue(
      SELF_PROFILE.id,
    );
    expect(screen.getByRole("button", { name: "Choose files" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Use camera" })).toBeEnabled();
  });

  it("sends one PDF and optional context, shows progress, and waits for durable receipt", async () => {
    const xhrs = mockUploadTransport();
    render(<UploadTab active onUnauthenticated={vi.fn()} />);
    await selectProfile();
    await selectFiles(pdf());
    await userEvent.type(
      screen.getByLabelText(/Report name/),
      "September report",
    );
    await userEvent.type(screen.getByLabelText(/Anything to add/), "A note");
    await userEvent.click(
      screen.getByRole("button", { name: "Upload report" }),
    );
    const xhr = xhrs[0]!;
    expect(xhr.open).toHaveBeenCalledWith(
      "POST",
      "/api/ingestions/direct-file",
    );
    expect(xhr.setRequestHeader).toHaveBeenCalledWith(
      "Authorization",
      "Bearer test-access-token",
    );
    expect(xhr.setRequestHeader).not.toHaveBeenCalledWith(
      "Content-Type",
      expect.anything(),
    );
    expect(xhr.body?.get("provisional_profile_id")).toBe(SELF_PROFILE.id);
    expect(xhr.body?.get("display_filename")).toBe("September report");
    expect(xhr.body?.get("user_context")).toBe("A note");
    expect(xhr.body?.has("source_channel")).toBe(false);
    expect(xhr.body?.getAll("uploads")).toHaveLength(1);
    act(() => xhr.progress(100));
    expect(screen.getByRole("status")).toHaveTextContent(
      "Validating and saving",
    );
    expect(
      screen.queryByRole("heading", { name: "Report uploaded" }),
    ).not.toBeInTheDocument();
    await act(async () => xhr.respond());
    expect(
      screen.getByRole("heading", { name: "Report uploaded" }),
    ).toHaveFocus();
    expect(screen.getByText("Awaiting assignment")).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "Upload another report" }),
    );
    expect(screen.queryByText("report.pdf")).not.toBeInTheDocument();
    expect(screen.getByLabelText(/Report name/)).toHaveValue("");
  });

  it("previews, reorders and removes pages before uploading one report", async () => {
    const xhrs = mockUploadTransport();
    render(<UploadTab active onUnauthenticated={vi.fn()} />);
    await selectProfile();
    await selectFiles([photo("one.png"), photo("two.png"), photo("three.png")]);
    expect(await screen.findAllByRole("img")).toHaveLength(3);
    await userEvent.click(
      screen.getByRole("button", { name: "Move page 2 up" }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Remove page 3" }),
    );
    expect(URL.revokeObjectURL).toHaveBeenCalledOnce();
    await userEvent.click(
      screen.getByRole("button", { name: "Upload report" }),
    );
    expect(
      xhrs[0]!.body?.getAll("uploads").map((file) => (file as File).name),
    ).toEqual(["two.png", "one.png"]);
  });

  it("keeps the draft while switching tabs and supports keyboard navigation", async () => {
    const { unmount } = render(
      <AppShell
        profile={<p>Family settings</p>}
        email="asha@example.com"
        onSignOut={vi.fn()}
        onUnauthenticated={vi.fn()}
      />,
    );
    await selectProfile();
    await selectFiles(photo("page.png"));
    await screen.findByRole("img");
    await userEvent.type(
      screen.getByLabelText(/Anything to add/),
      "Draft note",
    );
    await userEvent.click(screen.getByRole("tab", { name: "Chat" }));
    expect(
      within(screen.getByRole("tabpanel")).getByText(/Coming soon/),
    ).toBeVisible();
    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Upload" })).toHaveFocus();
    expect(screen.getByLabelText(/Anything to add/)).toHaveValue("Draft note");
    expect(screen.getByRole("img")).toBeInTheDocument();
    await userEvent.keyboard("{End}");
    expect(screen.getByText("Family settings")).toBeInTheDocument();
    unmount();
    expect(URL.revokeObjectURL).toHaveBeenCalledOnce();
  });

  it("rejects unsupported, empty, oversized and combined PDF files before requesting receipt", async () => {
    const xhrs = mockUploadTransport();
    render(<UploadTab active onUnauthenticated={vi.fn()} />);
    await selectProfile();
    const input = screen.getByLabelText("Report files");
    for (const [files, message] of [
      [
        [new File(["x"], "test.gif", { type: "image/gif" })],
        "Choose PDF, JPEG, or PNG",
      ],
      [[new File([], "test.pdf", { type: "application/pdf" })], "empty"],
      [[pdf(), photo("page.png")], "PDFs cannot be combined"],
      [
        [
          new File([new Uint8Array(10_000_001)], "large.png", {
            type: "image/png",
          }),
        ],
        "10 MB",
      ],
    ] as const) {
      fireEvent.change(input, { target: { files } });
      expect(await screen.findByRole("alert")).toHaveTextContent(message);
    }
    expect(xhrs).toHaveLength(0);
  });

  it("keeps selected files after a server rejection and allows a retry", async () => {
    const xhrs = mockUploadTransport();
    render(<UploadTab active onUnauthenticated={vi.fn()} />);
    await selectProfile();
    await selectFiles(pdf());
    await userEvent.click(
      screen.getByRole("button", { name: "Upload report" }),
    );
    await act(async () =>
      xhrs[0]!.respond(
        { detail: "This PDF is encrypted. Upload an unencrypted copy." },
        422,
      ),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("encrypted");
    expect(screen.getByText("report.pdf")).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "Upload report" }),
    );
    await act(async () => xhrs[1]!.respond());
    expect(
      screen.getByRole("heading", { name: "Report uploaded" }),
    ).toBeInTheDocument();
  });

  it("shows a saved upload even when extraction fails", async () => {
    const xhrs = mockUploadTransport();
    render(<UploadTab active onUnauthenticated={vi.fn()} />);
    await selectProfile();
    await selectFiles(pdf());
    await userEvent.click(
      screen.getByRole("button", { name: "Upload report" }),
    );
    await act(async () =>
      xhrs[0]!.respond({
        ...UPLOAD_RESULT,
        ingestion: { ...UPLOAD_RESULT.ingestion, extraction_state: "failed" },
      }),
    );
    expect(
      screen.getByRole("heading", { name: "Report uploaded" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Your upload is saved/)).toBeInTheDocument();
  });

  it("signs out on upload authentication failure and aborts transport on unmount", async () => {
    const xhrs = mockUploadTransport();
    const signOut = vi.fn();
    const { unmount } = render(
      <UploadTab active onUnauthenticated={signOut} />,
    );
    await selectProfile();
    await selectFiles(pdf());
    await userEvent.click(
      screen.getByRole("button", { name: "Upload report" }),
    );
    await act(async () => xhrs[0]!.respond({ detail: "Sign in again." }, 401));
    await waitFor(() => expect(signOut).toHaveBeenCalledOnce());
    await userEvent.click(
      screen.getByRole("button", { name: "Upload report" }),
    );
    unmount();
    expect(xhrs[1]!.abort).toHaveBeenCalledOnce();
  });

  it("distinguishes profile load errors from an empty family and retries", async () => {
    let failed = true;
    mockApi({
      "GET /profiles": () =>
        failed
          ? {
              status: 503,
              body: { detail: "Profiles temporarily unavailable." },
            }
          : { body: [SELF_PROFILE] },
    });
    render(<UploadTab active onUnauthenticated={vi.fn()} />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "temporarily unavailable",
    );
    expect(
      screen.queryByText(/Add a family member in Profile/),
    ).not.toBeInTheDocument();
    failed = false;
    await userEvent.click(
      screen.getByRole("button", { name: "Retry loading profiles" }),
    );
    await selectProfile();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("reports camera permission failure and closes capture when changing tabs", async () => {
    const getUserMedia = vi
      .fn()
      .mockRejectedValue(new DOMException("Denied", "NotAllowedError"));
    vi.stubGlobal(
      "navigator",
      Object.create(navigator, { mediaDevices: { value: { getUserMedia } } }),
    );
    render(
      <AppShell
        profile={null}
        email="asha@example.com"
        onSignOut={vi.fn()}
        onUnauthenticated={vi.fn()}
      />,
    );
    await selectProfile();
    await userEvent.click(screen.getByRole("button", { name: "Use camera" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Check camera permission",
    );
    expect(getUserMedia).toHaveBeenCalledWith(
      expect.objectContaining({ audio: false }),
    );
    await userEvent.click(screen.getByRole("tab", { name: "Drive" }));
    expect(screen.queryByLabelText("Camera preview")).not.toBeInTheDocument();
  });

  it("captures and retakes camera pages, stops the camera, and stamps source through the camera route", async () => {
    const stop = vi.fn();
    const getUserMedia = vi
      .fn()
      .mockResolvedValue({ getTracks: () => [{ stop }] });
    vi.stubGlobal(
      "navigator",
      Object.create(navigator, { mediaDevices: { value: { getUserMedia } } }),
    );
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({
      drawImage: vi.fn(),
    } as unknown as CanvasRenderingContext2D);
    vi.spyOn(HTMLCanvasElement.prototype, "toBlob").mockImplementation(
      (callback) => callback(new Blob(["capture"], { type: "image/jpeg" })),
    );
    const xhrs = mockUploadTransport();
    render(<UploadTab active onUnauthenticated={vi.fn()} />);
    await selectProfile();
    async function capture(button: string) {
      await userEvent.click(screen.getByRole("button", { name: button }));
      const video = screen.getByLabelText("Camera preview");
      Object.defineProperties(video, {
        videoWidth: { value: 1000 },
        videoHeight: { value: 1500 },
      });
      fireEvent.loadedData(video);
      await userEvent.click(
        screen.getByRole("button", { name: "Capture page" }),
      );
      await waitFor(() =>
        expect(
          screen.queryByLabelText("Camera preview"),
        ).not.toBeInTheDocument(),
      );
    }
    await capture("Use camera");
    const firstPreview = screen.getByRole("img").getAttribute("src");
    await capture("Retake page 1");
    expect(screen.getAllByRole("img")).toHaveLength(1);
    expect(screen.getByRole("img")).not.toHaveAttribute("src", firstPreview);
    expect(stop).toHaveBeenCalledTimes(2);
    await userEvent.click(
      screen.getByRole("button", { name: "Upload report" }),
    );
    expect(xhrs[0]!.open).toHaveBeenCalledWith(
      "POST",
      "/api/ingestions/camera",
    );
    expect((xhrs[0]!.body?.get("uploads") as File).type).toBe("image/jpeg");
  });
});
