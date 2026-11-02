import { useEffect, useRef, useState, type FormEvent } from "react";
import { ApiError } from "../api/client";
import {
  assignReport,
  getReport,
  retryReport,
  type FeedItem,
  type ReportExtraction,
} from "../api/feed";
import { listProfiles } from "../api/profiles";
import type { ProfileRead } from "../api/types";
import { ErrorBanner } from "../components/ErrorBanner";
import { formatReportedDate } from "../format";
import { assignedTo, reportDate, ReportState } from "./ReportState";

export function ReportDetail({
  item,
  onBack,
  onUnauthenticated,
}: {
  item: FeedItem;
  onBack: () => void;
  onUnauthenticated: () => void;
}) {
  const [data, setData] = useState<ReportExtraction | null>(null);
  const [profiles, setProfiles] = useState<ProfileRead[]>([]);
  const [profileId, setProfileId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const heading = useRef<HTMLHeadingElement>(null);
  const mounted = useRef(false);
  const mutation = useRef(false);
  const version = useRef(0);

  useEffect(() => {
    mounted.current = true;
    heading.current?.focus();
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    async function load() {
      const requestedVersion = version.current;
      try {
        const [report, family] = await Promise.all([
          getReport(item.id),
          listProfiles(),
        ]);
        if (
          cancelled ||
          mutation.current ||
          requestedVersion !== version.current
        )
          return;
        setData(report);
        setProfiles(family);
        setError(null);
      } catch (cause) {
        if (
          cancelled ||
          mutation.current ||
          requestedVersion !== version.current
        )
          return;
        if (cause instanceof ApiError && cause.status === 401)
          onUnauthenticated();
        else {
          if (cause instanceof ApiError && cause.status === 404) setData(null);
          setError(
            cause instanceof ApiError
              ? cause.message
              : "Could not load this report.",
          );
        }
      } finally {
        if (!cancelled)
          timer = setTimeout(() => {
            if (!document.hidden) void load();
          }, 5000);
      }
    }
    const refreshVisible = () => {
      if (!document.hidden) {
        clearTimeout(timer);
        setRevision((value) => value + 1);
      }
    };
    void load();
    document.addEventListener("visibilitychange", refreshVisible);
    return () => {
      cancelled = true;
      clearTimeout(timer);
      document.removeEventListener("visibilitychange", refreshVisible);
    };
  }, [item.id, revision, onUnauthenticated]);

  async function assign(event: FormEvent) {
    event.preventDefault();
    if (!profileId) return;
    await save(
      () => assignReport(item.id, profileId),
      "Family member assigned.",
    );
  }

  async function save(update: () => Promise<unknown>, message: string) {
    if (mutation.current) return;
    mutation.current = true;
    version.current += 1;
    setSaving(true);
    setActionError(null);
    setNotice(null);
    try {
      await update();
      if (!mounted.current) return;
      const report = await getReport(item.id);
      if (!mounted.current) return;
      setData(report);
      setNotice(message);
      heading.current?.focus();
    } catch (cause) {
      if (!mounted.current) return;
      if (cause instanceof ApiError && cause.status === 401)
        onUnauthenticated();
      else
        setActionError(
          cause instanceof ApiError
            ? cause.message
            : "Could not update this report. Try again.",
        );
    } finally {
      version.current += 1;
      mutation.current = false;
      if (mounted.current) setSaving(false);
    }
  }

  const ingestion = data?.ingestion;
  const assigned = profiles.find(
    (profile) => profile.id === ingestion?.resolved_profile_id,
  );
  const provisional = profiles.find(
    (profile) => profile.id === ingestion?.provisional_profile_id,
  );
  const metadataPending =
    data?.metadata_candidates.some(
      (candidate) => candidate.review_status === "pending",
    ) ?? false;
  const failedJob = data?.jobs.find((job) => job.status === "failed");

  return (
    <section className="flex flex-col gap-5">
      <button
        className="button button--quiet self-start"
        type="button"
        onClick={onBack}
      >
        ← Back to Feed
      </button>
      <div className="panel">
        <h2
          ref={heading}
          tabIndex={-1}
          className="text-2xl [overflow-wrap:anywhere]"
        >
          {data?.record?.display_filename ??
            ingestion?.display_filename ??
            item.display_filename}
        </h2>
        <ErrorBanner message={error} />
        <ErrorBanner message={actionError} />
        {error ? (
          <button
            className="button button--quiet self-start"
            type="button"
            onClick={() => setRevision((value) => value + 1)}
          >
            Reload report
          </button>
        ) : null}
        {notice ? (
          <p role="status" className="text-sage">
            {notice}
          </p>
        ) : null}
        {!data && !error ? (
          <p role="status" className="muted">
            Loading report…
          </p>
        ) : null}
        {data && ingestion ? (
          <>
            <dl className="grid gap-4 text-sm sm:grid-cols-2">
              <div>
                <dt className="muted">Family member</dt>
                <dd className="m-0 font-medium">
                  {assignedTo(assigned?.display_name, ingestion.assignment_state)}
                </dd>
              </div>
              <div>
                <dt className="muted">Source</dt>
                <dd className="m-0">
                  {ingestion.source_channel === "camera"
                    ? "Camera capture"
                    : "File upload"}
                </dd>
              </div>
              <div>
                <dt className="muted">Uploaded</dt>
                <dd className="m-0">
                  {formatReportedDate(ingestion.completed_at)}
                </dd>
              </div>
              <div>
                <dt className="muted">Report date</dt>
                <dd className="m-0">
                  {reportDate(data.record?.record_date ?? null)}
                </dd>
              </div>
            </dl>
            <ReportState
              assignment={ingestion.assignment_state}
              extraction={ingestion.extraction_state}
              review={ingestion.review_state}
              metadataPending={metadataPending}
            />
            {assigned && provisional && assigned.id !== provisional.id ? (
              <p className="muted text-sm">
                Selected for {provisional.display_name} at upload; assigned to{" "}
                {assigned.display_name} after patient matching or your
                assignment decision.
              </p>
            ) : null}
            {["queued", "extracting", "retrying"].includes(
              ingestion.extraction_state,
            ) ? (
              <p role="status" className="muted">
                Your upload is saved. Processing continues here, and this status
                updates automatically.
              </p>
            ) : null}
            {ingestion.extraction_state === "failed" ? (
              <p className="muted">
                Your upload is saved, but its information could not be
                extracted. No new medical information was published from the
                failed attempt.
              </p>
            ) : null}
            {ingestion.extraction_state === "failed" &&
            failedJob?.failure_code === "extraction_failed" ? (
              <button
                className="button self-start"
                type="button"
                disabled={saving}
                onClick={() =>
                  void save(
                    () => retryReport(failedJob.id),
                    "Extraction retry requested. Check the updated status.",
                  )
                }
              >
                {saving ? "Retrying extraction…" : "Retry extraction"}
              </button>
            ) : null}
            {ingestion.assignment_state === "needs_assignment" &&
            ingestion.extraction_state === "ready" ? (
              <form
                className="border-line flex flex-col gap-4 border-t pt-5"
                onSubmit={(event) => void assign(event)}
              >
                <h3 className="text-lg">Choose who this report belongs to</h3>
                <p className="muted text-sm">
                  We could not match the patient to one family member. Check the
                  patient details before assigning the report.
                </p>
                {data.patient_evidence.length ? (
                  <ul className="flex flex-col gap-2">
                    {data.patient_evidence.map((evidence) => (
                      <li
                        key={evidence.id}
                        className="bg-surface-sunk rounded-xl p-3 text-sm"
                      >
                        <p>
                          Patient name in document:{" "}
                          <strong>{evidence.extracted_name}</strong>
                        </p>
                        {data.source_references
                          .filter(
                            (source) =>
                              source.patient_evidence_id === evidence.id,
                          )
                          .map((source) => (
                            <blockquote
                              key={source.id}
                              className="muted mt-2 [overflow-wrap:anywhere]"
                            >
                              Page {source.logical_page}: “{source.text_span}”
                            </blockquote>
                          ))}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted text-sm">
                    No patient name was extracted from this report.
                  </p>
                )}
                <div className="field">
                  <label className="field__label" htmlFor="assignment-profile">
                    Family member
                  </label>
                  <select
                    id="assignment-profile"
                    className="input"
                    value={profileId}
                    disabled={saving}
                    required
                    onChange={(event) => setProfileId(event.target.value)}
                  >
                    <option value="">Select a family member</option>
                    {profiles.map((profile) => (
                      <option key={profile.id} value={profile.id}>
                        {profile.display_name} ({profile.relationship})
                      </option>
                    ))}
                  </select>
                </div>
                {!profiles.length ? (
                  <p className="muted text-sm">
                    Add a family member in Profile, then return here.
                  </p>
                ) : null}
                <button
                  className="button self-start"
                  type="submit"
                  disabled={!profileId || saving}
                >
                  {saving ? "Assigning…" : "Assign report"}
                </button>
              </form>
            ) : null}
            {metadataPending || ingestion.review_state === "pending" ? (
              <p className="muted text-sm">
                Extracted information is awaiting review. Review editing will be
                available in a later update.
              </p>
            ) : null}
            {ingestion.assignment_state === "resolved" &&
            data.observations.length ? (
              <section className="border-line border-t pt-5">
                <h3 className="text-lg">Extracted measurements</h3>
                <p className="muted mt-1 text-sm">
                  Unreviewed values from this report. These are not trusted
                  medical memory.
                </p>
                <ul className="mt-3 flex flex-col gap-3">
                  {data.observations.map((observation) => (
                    <li key={observation.id}>
                      <strong>{observation.label}</strong>:{" "}
                      {Object.values(observation.original_value)
                        .filter(
                          (value) =>
                            typeof value === "string" ||
                            typeof value === "number",
                        )
                        .join(" · ")}{" "}
                      {observation.original_unit}
                      {data.source_references
                        .filter(
                          (source) =>
                            source.metric_observation_id === observation.id,
                        )
                        .map((source) => (
                          <blockquote
                            key={source.id}
                            className="muted text-sm [overflow-wrap:anywhere]"
                          >
                            Page {source.logical_page}: “{source.text_span}”
                          </blockquote>
                        ))}
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
            {ingestion.user_context ? (
              <div className="border-line border-t pt-4">
                <h3 className="text-base">Your upload note</h3>
                <p className="muted mt-1 whitespace-pre-wrap [overflow-wrap:anywhere]">
                  {ingestion.user_context}
                </p>
              </div>
            ) : null}
          </>
        ) : null}
      </div>
    </section>
  );
}
