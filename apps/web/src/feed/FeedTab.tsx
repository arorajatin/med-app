import { useEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";
import {
  FEED_MAX_LIMIT,
  listFeed,
  type FeedItem,
  type FeedOrder,
  type FeedPage,
} from "../api/feed";
import { listProfiles } from "../api/profiles";
import type { ProfileRead } from "../api/types";
import { ErrorBanner } from "../components/ErrorBanner";
import { formatReportedDate } from "../format";
import { ReportDetail } from "./ReportDetail";
import { assignedTo, reportDate, ReportState } from "./ReportState";

/** How many reports one “Load more” press adds, matching the API's default page. */
const PAGE_SIZE = 20;

export function FeedTab({
  onOpenUpload,
  onUnauthenticated,
  uploadedId,
}: {
  onOpenUpload: () => void;
  onUnauthenticated: () => void;
  uploadedId: string | null;
}) {
  const [order, setOrder] = useState<FeedOrder>("upload_date");
  const [selected, setSelected] = useState<FeedItem | null>(null);
  const [revision, setRevision] = useState(0);
  const [pages, setPages] = useState(1);
  const [focusId, setFocusId] = useState(uploadedId);
  const [profileId, setProfileId] = useState<string | null>(null);
  const [profiles, setProfiles] = useState<ProfileRead[] | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileRevision, setProfileRevision] = useState(0);

  useEffect(() => {
    let cancelled = false;
    listProfiles()
      .then((result) => {
        if (cancelled) return;
        setProfiles(result);
        setProfileError(null);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof ApiError && cause.status === 401)
          onUnauthenticated();
        else
          setProfileError(
            "Could not load family members. All Family is still available.",
          );
      });
    return () => {
      cancelled = true;
    };
  }, [profileRevision, onUnauthenticated]);

  function selectProfile(id: string | null) {
    setPages(1);
    setFocusId(null);
    setProfileId(id);
  }

  if (selected) {
    return (
      <ReportDetail
        item={selected}
        onUnauthenticated={onUnauthenticated}
        onBack={() => {
          setSelected(null);
          setRevision((value) => value + 1);
        }}
      />
    );
  }
  return (
    <section className="flex flex-col gap-5" aria-label="Family feed">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl">Your family’s reports</h2>
          <p className="muted mt-1 text-sm">
            Every completed upload, across your family.
          </p>
        </div>
        <button className="button" type="button" onClick={onOpenUpload}>
          Add a report
        </button>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="field">
          <label className="field__label" htmlFor="feed-profile">
            Family view
          </label>
          <select
            id="feed-profile"
            className="input"
            value={profileId ?? ""}
            disabled={profiles === null}
            onChange={(event) => selectProfile(event.target.value || null)}
          >
            <option value="">All Family</option>
            {profiles?.map((profile) => (
              <option key={profile.id} value={profile.id}>
                {profile.display_name} ({profile.relationship})
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label className="field__label" htmlFor="feed-order">
            Order by
          </label>
          <select
            id="feed-order"
            className="input"
            value={order}
            onChange={(event) => {
              setPages(1);
              setFocusId(null);
              setOrder(event.target.value as FeedOrder);
            }}
          >
            <option value="upload_date">Upload date · newest first</option>
            <option value="report_date">Report date · newest first</option>
          </select>
        </div>
      </div>
      {profileError ? (
        <div className="flex flex-col items-start gap-2">
          <ErrorBanner message={profileError} />
          <button
            className="button button--quiet"
            type="button"
            onClick={() => {
              setProfileError(null);
              setProfileRevision((value) => value + 1);
            }}
          >
            Retry family members
          </button>
        </div>
      ) : null}
      {order === "report_date" ? (
        <p className="muted text-sm">
          Only confirmed report dates set this order. Undated reports appear
          last.
        </p>
      ) : null}
      <FeedResults
        key={`${profileId ?? "all"}-${order}-${revision}`}
        order={order}
        profileId={profileId}
        profileName={
          profiles?.find((profile) => profile.id === profileId)?.display_name ??
          "this family member"
        }
        onShowAll={() => selectProfile(null)}
        onOpen={(item) => {
          setFocusId(item.id);
          setSelected(item);
        }}
        onOpenUpload={onOpenUpload}
        onUnauthenticated={onUnauthenticated}
        uploadedId={uploadedId}
        focusId={focusId}
        pages={pages}
        onLoadMore={() => setPages((value) => value + 1)}
      />
    </section>
  );
}

function FeedResults({
  order,
  profileId,
  profileName,
  onShowAll,
  onOpen,
  onOpenUpload,
  onUnauthenticated,
  uploadedId,
  focusId,
  pages,
  onLoadMore,
}: {
  order: FeedOrder;
  profileId: string | null;
  profileName: string;
  onShowAll: () => void;
  onOpen: (item: FeedItem) => void;
  onOpenUpload: () => void;
  onUnauthenticated: () => void;
  uploadedId: string | null;
  focusId: string | null;
  pages: number;
  onLoadMore: () => void;
}) {
  const [items, setItems] = useState<FeedItem[] | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const uploaded = useRef<HTMLButtonElement>(null);
  const focused = useRef(false);

  useEffect(() => {
    let cancelled = false;
    let running = false;
    let timer: ReturnType<typeof setTimeout>;
    async function load() {
      if (running || cancelled) return;
      running = true;
      clearTimeout(timer);
      try {
        // Rebuild the loaded pages together so date/assignment changes cannot
        // leave stale copies behind or reset the list to the first page. Ask for
        // them in as few requests as the page limit allows: polling every five
        // seconds must not cost a round-trip per page the manager has opened.
        const loaded = new Map<string, FeedItem>();
        let cursor: string | null = null;
        let remaining = pages * PAGE_SIZE;
        while (remaining > 0) {
          const size = Math.min(remaining, FEED_MAX_LIMIT);
          const result: FeedPage = await listFeed(
            order,
            cursor,
            size,
            profileId,
          );
          if (cancelled) return;
          result.items.forEach((item) => loaded.set(item.id, item));
          remaining -= size;
          cursor = result.next_cursor;
          if (!cursor) break;
        }
        setItems([...loaded.values()]);
        setHasMore(cursor !== null);
        setError(null);
      } catch (cause) {
        if (cancelled) return;
        if (cause instanceof ApiError && cause.status === 401)
          onUnauthenticated();
        else
          setError(
            cause instanceof ApiError
              ? cause.message
              : "Could not load your reports.",
          );
      } finally {
        running = false;
        if (!cancelled) {
          setLoading(false);
          timer = setTimeout(() => {
            if (!document.hidden) void load();
          }, 5000);
        }
      }
    }
    const refreshVisible = () => {
      if (!document.hidden) void load();
    };
    void load();
    window.addEventListener("focus", refreshVisible);
    document.addEventListener("visibilitychange", refreshVisible);
    return () => {
      cancelled = true;
      clearTimeout(timer);
      window.removeEventListener("focus", refreshVisible);
      document.removeEventListener("visibilitychange", refreshVisible);
    };
  }, [order, profileId, pages, revision, onUnauthenticated]);

  useEffect(() => {
    if (uploaded.current && !focused.current) {
      uploaded.current.focus();
      focused.current = true;
    }
  }, [items]);

  return (
    <>
      <ErrorBanner message={error} />
      <div className="flex items-center justify-between gap-3">
        <p className="muted text-sm" role="status">
          {loading
            ? "Loading reports…"
            : error
              ? "Automatic updates will retry. You can also refresh."
              : "Status updates automatically."}
        </p>
        <button
          className="button button--quiet"
          type="button"
          disabled={loading}
          onClick={() => {
            setLoading(true);
            setRevision((value) => value + 1);
          }}
        >
          Refresh
        </button>
      </div>
      {items?.length === 0 && !error ? (
        <div className="panel items-center py-12 text-center">
          <h3 className="text-xl">
            {profileId
              ? `No reports for ${profileName}`
              : "Your reports will appear here"}
          </h3>
          <p className="muted max-w-md">
            {profileId
              ? "Reports appear here once assigned to this person. Uploads still being matched to a family member are in All Family."
              : "Upload a report for anyone in your family. You can follow its progress here as soon as it is saved."}
          </p>
          <button
            className="button"
            type="button"
            onClick={profileId ? onShowAll : onOpenUpload}
          >
            {profileId ? "View All Family" : "Upload your first report"}
          </button>
        </div>
      ) : null}
      <ol className="flex flex-col gap-4" aria-label="Reports">
        {items?.map((item) => (
          <li
            key={item.id}
            className={`panel gap-3 ${item.id === uploadedId ? "ring-sage/50 ring-2" : ""}`}
          >
            <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <span className="text-sage font-medium">
                {assignedTo(item.profile?.display_name, item.assignment_state)}
              </span>
              <span className="muted">{item.source_label}</span>
            </div>
            <h3 className="text-xl [overflow-wrap:anywhere]">
              <button
                ref={item.id === focusId ? uploaded : undefined}
                className="text-left hover:underline"
                type="button"
                onClick={() => onOpen(item)}
              >
                {item.display_filename}
              </button>
            </h3>
            {item.id === uploadedId ? (
              <p className="text-sage text-sm font-medium">
                Just uploaded · saved privately
              </p>
            ) : null}
            <dl className="flex flex-wrap gap-x-8 gap-y-2 text-sm">
              <div>
                <dt className="muted">Uploaded</dt>
                <dd className="m-0">{formatReportedDate(item.completed_at)}</dd>
              </div>
              <div>
                <dt className="muted">Report date</dt>
                <dd className="m-0">{reportDate(item.report_date)}</dd>
              </div>
            </dl>
            <ReportState
              assignment={item.assignment_state}
              extraction={item.extraction_state}
              review={item.review_state}
              metadataPending={item.metadata_review_pending}
            />
            <button
              className="button button--quiet self-start"
              type="button"
              onClick={() => onOpen(item)}
              aria-label={`Open ${item.display_filename}`}
            >
              {item.assignment_state === "needs_assignment" &&
              item.extraction_state === "ready"
                ? "Assign family member"
                : "View report details"}
            </button>
          </li>
        ))}
      </ol>
      {hasMore ? (
        <button
          className="button button--quiet self-center"
          type="button"
          disabled={loading}
          onClick={() => {
            setLoading(true);
            onLoadMore();
          }}
        >
          Load more reports
        </button>
      ) : null}
    </>
  );
}
