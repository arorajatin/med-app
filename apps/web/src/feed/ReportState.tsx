export function ReportState({
  assignment,
  extraction,
  review,
  metadataPending,
}: {
  assignment: string;
  extraction: string;
  review: string;
  metadataPending: boolean;
}) {
  const processing: Record<string, string> = {
    queued: "Queued for extraction",
    extracting: "Extracting report",
    retrying: "Retrying extraction",
    failed: "Extraction failed",
    ready: "Extraction complete",
    not_requested: "Waiting for extraction",
  };
  return (
    <ul
      aria-label="Report status"
      className="flex flex-wrap gap-2 text-xs font-medium"
    >
      <li
        className={`rounded-full px-3 py-1 ${extraction === "failed" ? "bg-honey-soft text-ink" : "bg-surface-sunk text-ink-soft"}`}
      >
        {processing[extraction] ?? "Processing status unavailable"}
      </li>
      {assignment !== "resolved" ? (
        <li className="bg-honey-soft text-ink rounded-full px-3 py-1">
          {assignment === "needs_assignment"
            ? "Needs assignment"
            : "Patient match pending"}
        </li>
      ) : null}
      {metadataPending ? (
        <li className="bg-honey-soft text-ink rounded-full px-3 py-1">
          Report details need review
        </li>
      ) : null}
      {review === "pending" ? (
        <li className="bg-honey-soft text-ink rounded-full px-3 py-1">
          Medical review pending
        </li>
      ) : review === "reviewed" ? (
        <li className="bg-sage-soft text-sage rounded-full px-3 py-1">
          Medical review complete
        </li>
      ) : extraction === "ready" ? (
        <li className="bg-surface-sunk text-ink-soft rounded-full px-3 py-1">
          No medical review needed
        </li>
      ) : null}
    </ul>
  );
}

/**
 * A report only names a family member once its patient details confirm one.
 * Until then the manager's upload choice is still provisional, so say the match
 * is being checked rather than asking for an assignment nobody owes yet.
 */
export function assignedTo(
  displayName: string | undefined,
  assignment: string,
): string {
  if (displayName) return displayName;
  return assignment === "needs_assignment"
    ? "Needs assignment"
    : "Checking patient details";
}

/** Report dates are calendar days, so never shift them into the viewer's time zone. */
export function reportDate(value: string | null): string {
  if (!value) return "Not confirmed";
  return new Date(`${value}T00:00:00Z`).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}
