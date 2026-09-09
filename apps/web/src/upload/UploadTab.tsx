import { useEffect, useRef, useState, type FormEvent } from "react";
import { ApiError } from "../api/client";
import {
  uploadDocument,
  type IngestionUploadResult,
  type UploadSource,
} from "../api/ingestions";
import { listProfiles } from "../api/profiles";
import type { ProfileRead } from "../api/types";
import { ErrorBanner } from "../components/ErrorBanner";
import { CameraCapture } from "./CameraCapture";
import { fileKind, validateFiles, validateImage } from "./validation";

interface Page {
  id: string;
  file: File;
  preview: string | null;
}

export function UploadTab({
  active,
  onUnauthenticated,
}: {
  active: boolean;
  onUnauthenticated: () => void;
}) {
  const [profiles, setProfiles] = useState<ProfileRead[] | null>(null);
  const [profileId, setProfileId] = useState("");
  const [profileError, setProfileError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const [pages, setPages] = useState<Page[]>([]);
  const [source, setSource] = useState<UploadSource>("direct_file");
  const [cameraOpen, setCameraOpen] = useState(false);
  const [retakeId, setRetakeId] = useState<string | null>(null);
  const [displayFilename, setDisplayFilename] = useState("");
  const [context, setContext] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [result, setResult] = useState<IngestionUploadResult | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const selection = useRef<HTMLSelectElement>(null);
  const receipt = useRef<HTMLHeadingElement>(null);
  const request = useRef<AbortController | null>(null);
  const previewUrls = useRef(new Set<string>());
  const mounted = useRef(false);
  const busy = checking || progress !== null;

  useEffect(() => {
    mounted.current = true;
    const urls = previewUrls.current;
    return () => {
      mounted.current = false;
      request.current?.abort();
      urls.forEach((url) => URL.revokeObjectURL(url));
      urls.clear();
    };
  }, []);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    listProfiles()
      .then((loaded) => {
        if (cancelled) return;
        setProfiles(loaded);
        setProfileError(null);
        setProfileId((current) => {
          if (loaded.some((profile) => profile.id === current)) return current;
          // Most reports are the account holder's own, so open on that profile.
          // It stays a provisional choice: the report's patient details decide.
          const fallback =
            loaded.find((profile) => profile.relationship === "self") ?? loaded[0];
          return fallback?.id ?? "";
        });
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof ApiError && cause.status === 401)
          onUnauthenticated();
        else
          setProfileError(
            cause instanceof ApiError
              ? cause.message
              : "Could not load your family profiles.",
          );
      });
    return () => {
      cancelled = true;
    };
  }, [active, onUnauthenticated, reload]);

  useEffect(() => {
    if (result && active) receipt.current?.focus();
  }, [result, active]);

  function release(page: Page) {
    if (page.preview) {
      URL.revokeObjectURL(page.preview);
      previewUrls.current.delete(page.preview);
    }
  }

  async function addFiles(
    files: File[],
    nextSource: UploadSource,
    replaceId: string | null = null,
  ) {
    const firstFile = files[0];
    if (!firstFile || !profileId || busy) return;
    const candidate = replaceId
      ? pages.map((page) => (page.id === replaceId ? firstFile : page.file))
      : [...pages.map((page) => page.file), ...files];
    const invalid = validateFiles(candidate, nextSource === "camera");
    if (invalid) {
      setError(invalid);
      return;
    }
    setChecking(true);
    setError(null);
    try {
      await Promise.all(
        files.filter((file) => fileKind(file) === "image").map(validateImage),
      );
      if (!mounted.current) return;
      const added = files.map((file) => {
        const preview =
          fileKind(file) === "image" ? URL.createObjectURL(file) : null;
        if (preview) previewUrls.current.add(preview);
        return { id: crypto.randomUUID(), file, preview };
      });
      const firstAdded = added[0];
      if (replaceId && firstAdded) {
        const replaced = pages.find((page) => page.id === replaceId);
        if (replaced) release(replaced);
        setPages(
          pages.map((page) => (page.id === replaceId ? firstAdded : page)),
        );
      } else setPages([...pages, ...added]);
      setSource(nextSource);
      setCameraOpen(false);
      setRetakeId(null);
    } catch (cause) {
      if (mounted.current)
        setError(
          cause instanceof Error ? cause.message : "Could not open this file.",
        );
    } finally {
      if (mounted.current) setChecking(false);
    }
  }

  function move(index: number, offset: number) {
    const reordered = [...pages];
    const page = reordered[index];
    const neighbor = reordered[index + offset];
    if (!page || !neighbor) return;
    [reordered[index], reordered[index + offset]] = [neighbor, page];
    setPages(reordered);
  }

  function clearPages() {
    pages.forEach(release);
    setPages([]);
    setCameraOpen(false);
    setRetakeId(null);
    setError(null);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy || request.current) return;
    if (!profileId) {
      setError("Select a family profile before uploading.");
      selection.current?.focus();
      return;
    }
    const invalid = validateFiles(
      pages.map((page) => page.file),
      source === "camera",
    );
    if (invalid) {
      setError(invalid);
      return;
    }
    setError(null);
    setCameraOpen(false);
    setProgress(0);
    const controller = new AbortController();
    request.current = controller;
    try {
      const uploaded = await uploadDocument(
        {
          files: pages.map((page) => page.file),
          profileId,
          source,
          displayFilename,
          context,
        },
        (percent) => {
          if (mounted.current) setProgress(percent);
        },
        controller.signal,
      );
      if (!mounted.current) return;
      setResult(uploaded);
      clearPages();
      setDisplayFilename("");
      setContext("");
    } catch (cause) {
      if (!mounted.current || controller.signal.aborted) return;
      if (cause instanceof ApiError && cause.status === 401)
        onUnauthenticated();
      else
        setError(
          cause instanceof ApiError
            ? cause.message
            : "Could not upload the report. Try again.",
        );
    } finally {
      request.current = null;
      if (mounted.current) setProgress(null);
    }
  }

  if (result) {
    const assignedProfile = profiles?.find(
      (profile) => profile.id === result.ingestion.resolved_profile_id,
    );
    return (
      <section className="panel">
        <div className="flex items-center gap-4">
          <span
            className="bg-sage-soft text-sage ring-sage/25 flex h-14 w-14 flex-none items-center justify-center rounded-full text-2xl ring-1"
            aria-hidden="true"
          >
            ✓
          </span>
          <div className="min-w-0">
            <h2 ref={receipt} tabIndex={-1} className="text-2xl">
              Report uploaded
            </h2>
            <p className="muted mt-1 [overflow-wrap:anywhere]">
              <strong className="text-ink">
                {result.ingestion.display_filename}
              </strong>{" "}
              is stored privately.
            </p>
          </div>
        </div>
        <dl className="divide-line border-line flex flex-col divide-y rounded-2xl border px-4">
          <div className="flex justify-between gap-4 py-3">
            <dt className="muted">Upload</dt>
            <dd className="m-0 text-right font-medium">
              Complete · {result.parts.length}{" "}
              {result.parts.length === 1 ? "file" : "pages"}
            </dd>
          </div>
          <div className="flex justify-between gap-4 py-3">
            <dt className="muted">Processing</dt>
            <dd className="m-0 text-right font-medium">
              {result.ingestion.extraction_state === "failed"
                ? "Could not process this report. Your upload is saved."
                : result.ingestion.extraction_state === "ready"
                  ? "Extraction complete"
                  : "Queued for extraction"}
            </dd>
          </div>
          <div className="flex justify-between gap-4 py-3">
            <dt className="muted">Profile</dt>
            <dd className="m-0 text-right font-medium">
              {result.ingestion.assignment_state === "resolved"
                ? assignedProfile
                  ? `Assigned · ${assignedProfile.display_name}`
                  : "Assigned"
                : "Awaiting assignment"}
            </dd>
          </div>
        </dl>
        {assignedProfile &&
          result.ingestion.resolved_profile_id !== result.ingestion.provisional_profile_id && (
            <p className="muted text-sm">
              The patient name in this report matched {assignedProfile.display_name}.
              The report’s assignment has changed from your initial selection.
            </p>
          )}
        <p className="muted text-sm">
          Uploading a report does not confirm its extracted health information.
        </p>
        <button
          className="button"
          type="button"
          onClick={() => {
            setResult(null);
          }}
        >
          Upload another report
        </button>
      </section>
    );
  }

  const hasPdf = pages.some((page) => fileKind(page.file) === "pdf");
  return (
    <form className="panel" onSubmit={(event) => void submit(event)}>
      <div>
        <p className="eyebrow">Your family’s records</p>
        <h2 className="mt-2 text-2xl">Upload a report</h2>
        <p className="muted mt-2">
          Keep a lab report or prescription together, even when it spans several
          pages.
        </p>
      </div>
      <div className="field">
        <label className="field__label" htmlFor="upload-profile">
          Who is this report for?
        </label>
        <select
          ref={selection}
          id="upload-profile"
          className="input"
          value={profileId}
          disabled={busy || profiles === null || !!profileError}
          onChange={(event) => setProfileId(event.target.value)}
          aria-describedby="upload-profile-hint"
        >
          <option value="">
            {profiles === null
              ? "Loading family profiles…"
              : "Select a family profile"}
          </option>
          {profiles?.map((profile) => (
            <option key={profile.id} value={profile.id}>
              {profile.display_name} ·{" "}
              {profile.relationship === "self" ? "You" : profile.relationship}
            </option>
          ))}
        </select>
        <p className="field__hint" id="upload-profile-hint">
          This is a starting selection. The patient details in the report will
          be checked before assignment.
        </p>
        {profiles?.length === 0 ? (
          <p className="field__hint">
            Add a family member in Profile to get started.
          </p>
        ) : null}
        <ErrorBanner message={profileError} />
        {profileError ? (
          <button
            type="button"
            className="button button--quiet"
            onClick={() => setReload((count) => count + 1)}
          >
            Retry loading profiles
          </button>
        ) : null}
      </div>
      <fieldset
        className="border-sage/35 bg-sage-soft/60 m-0 flex min-w-0 flex-col gap-3.5 rounded-[1.25rem] border border-dashed p-5 disabled:opacity-60"
        disabled={!profileId || !!profileError || busy}
      >
        <legend className="field__label px-1.5">Add your document</legend>
        <p className="muted text-sm">
          One PDF or up to 20 images of the same report.
        </p>
        <div className="flex flex-wrap gap-2.5">
          <button
            className="button"
            type="button"
            disabled={hasPdf || (pages.length > 0 && source === "camera")}
            onClick={() => input.current?.click()}
          >
            {pages.length && source === "direct_file"
              ? "Add more images"
              : "Choose files"}
          </button>
          <button
            className="button button--quiet"
            type="button"
            disabled={pages.length > 0 && source === "direct_file"}
            onClick={() => {
              setRetakeId(null);
              setCameraOpen(true);
            }}
          >
            {pages.length && source === "camera"
              ? "Capture another page"
              : "Use camera"}
          </button>
        </div>
        <input
          ref={input}
          className="visually-hidden"
          tabIndex={-1}
          type="file"
          aria-label="Report files"
          accept="application/pdf,image/jpeg,image/png,.pdf,.jpg,.jpeg,.png"
          multiple
          onChange={(event) => {
            const files = Array.from(event.target.files ?? []);
            event.target.value = "";
            void addFiles(files, "direct_file");
          }}
        />
        <p className="field__hint">
          PDF, JPEG or PNG · 15 MB per report · 10 MB per image
        </p>
      </fieldset>
      {cameraOpen && active && profileId ? (
        <CameraCapture
          onCapture={(file) => addFiles([file], "camera", retakeId)}
          onClose={() => {
            setCameraOpen(false);
            setRetakeId(null);
          }}
        />
      ) : null}
      <ErrorBanner message={error} />
      {checking ? (
        <p role="status" className="muted">
          Checking your images…
        </p>
      ) : null}
      {pages.length ? (
        <section aria-label="Selected report pages">
          <div className="mb-3 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <h3 className="text-base">
              {hasPdf
                ? "Selected PDF"
                : `${pages.length} ${pages.length === 1 ? "page" : "pages"} · one report`}
            </h3>
            <span className="muted text-sm">
              {(
                pages.reduce((total, page) => total + page.file.size, 0) /
                1_000_000
              ).toFixed(2)}{" "}
              MB
            </span>
          </div>
          <ol className="flex flex-col gap-2.5">
            {pages.map((page, index) => (
              <li
                className="border-line bg-surface-sunk/50 flex items-start gap-3.5 rounded-2xl border p-3"
                key={page.id}
              >
                {page.preview ? (
                  <a
                    href={page.preview}
                    target="_blank"
                    rel="noreferrer"
                    aria-label={`Preview page ${index + 1}`}
                  >
                    <img
                      className="border-line bg-canvas block h-24 w-[4.5rem] rounded-lg border object-contain"
                      src={page.preview}
                      alt={`Page ${index + 1}`}
                    />
                  </a>
                ) : (
                  <span
                    className="border-line bg-canvas text-sage flex h-24 w-[4.5rem] flex-none items-center justify-center rounded-lg border text-sm font-bold"
                    aria-hidden="true"
                  >
                    PDF
                  </span>
                )}
                <div className="flex min-w-0 flex-col gap-1.5 [overflow-wrap:anywhere]">
                  <strong>{hasPdf ? "PDF" : `Page ${index + 1}`}</strong>
                  <span className="muted text-sm">{page.file.name}</span>
                  <div className="mt-1 flex flex-wrap gap-2">
                    {!hasPdf ? (
                      <>
                        <button
                          className="button button--quiet min-h-0 px-3 py-1.5 text-sm"
                          type="button"
                          aria-label={`Move page ${index + 1} up`}
                          disabled={busy || index === 0}
                          onClick={() => move(index, -1)}
                        >
                          ↑
                        </button>
                        <button
                          className="button button--quiet min-h-0 px-3 py-1.5 text-sm"
                          type="button"
                          aria-label={`Move page ${index + 1} down`}
                          disabled={busy || index === pages.length - 1}
                          onClick={() => move(index, 1)}
                        >
                          ↓
                        </button>
                      </>
                    ) : null}
                    {source === "camera" ? (
                      <button
                        className="button button--quiet min-h-0 px-3 py-1.5 text-sm"
                        type="button"
                        disabled={busy}
                        aria-label={`Retake page ${index + 1}`}
                        onClick={() => {
                          setRetakeId(page.id);
                          setCameraOpen(true);
                        }}
                      >
                        Retake
                      </button>
                    ) : null}
                    <button
                      className="button button--quiet min-h-0 px-3 py-1.5 text-sm"
                      type="button"
                      disabled={busy}
                      aria-label={`Remove ${hasPdf ? "PDF" : `page ${index + 1}`}`}
                      onClick={() => {
                        release(page);
                        setPages(pages.filter((item) => item.id !== page.id));
                        setError(null);
                        setCameraOpen(false);
                      }}
                    >
                      Remove
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ol>
          <button
            className="button button--quiet mt-3"
            type="button"
            disabled={busy}
            onClick={clearPages}
          >
            Clear document
          </button>
        </section>
      ) : null}
      <div className="field">
        <label className="field__label" htmlFor="report-name">
          Report name <span className="muted">(optional)</span>
        </label>
        <input
          id="report-name"
          className="input"
          maxLength={260}
          value={displayFilename}
          disabled={busy}
          placeholder="e.g. September blood test"
          onChange={(event) => setDisplayFilename(event.target.value)}
        />
      </div>
      <div className="field">
        <label className="field__label" htmlFor="upload-context">
          Anything to add? <span className="muted">(optional)</span>
        </label>
        <textarea
          id="upload-context"
          className="input"
          rows={3}
          maxLength={4000}
          value={context}
          disabled={busy}
          placeholder="A note to help you remember this report"
          onChange={(event) => setContext(event.target.value)}
          aria-describedby="upload-context-hint"
        />
        <p className="field__hint" id="upload-context-hint">
          Saved as your note, separate from information in the document.
        </p>
      </div>
      {progress !== null ? (
        <div
          role="status"
          className="border-line bg-surface-sunk/60 rounded-2xl border p-4"
        >
          <label className="text-sm font-medium" htmlFor="upload-progress">
            {progress < 100
              ? `Uploading… ${progress}%`
              : "Upload sent. Validating and saving your report…"}
          </label>
          <progress
            className="accent-sage mt-2 block w-full"
            id="upload-progress"
            max={100}
            value={progress}
          />
        </div>
      ) : null}
      <div className="border-line bg-surface/95 sticky bottom-[calc(4.75rem+env(safe-area-inset-bottom))] z-10 -mx-6 -mb-6 flex flex-wrap items-center gap-x-4 gap-y-3 rounded-b-[var(--radius-card)] border-t px-6 py-4 backdrop-blur-md sm:-mx-8 sm:-mb-8 sm:px-8 lg:bottom-0">
        <button
          className="button"
          type="submit"
          disabled={!profileId || !!profileError || !pages.length || busy}
        >
          {progress !== null ? "Uploading…" : "Upload report"}
        </button>
        <p className="field__hint">
          Stored privately. AI extraction begins after upload.
        </p>
      </div>
    </form>
  );
}
