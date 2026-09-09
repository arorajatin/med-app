import type { ProfileHealthContextSummary } from "../api/types";
import { formatDecimal, formatReportedDate } from "../format";

interface RecordedHealthContextProps {
  healthContext: ProfileHealthContextSummary | null;
}

/**
 * The latest reported age and weight, each with the date it was reported. A
 * stale value stays visible and is only marked as worth updating; nothing here
 * blocks the person or judges the value.
 */
export function RecordedHealthContext({ healthContext }: RecordedHealthContextProps) {
  if (
    healthContext === null ||
    (healthContext.reported_age === null && healthContext.entered_weight === null)
  ) {
    return <span className="muted">Not recorded yet.</span>;
  }
  return (
    <ul className="prose-list">
      {healthContext.reported_age === null ? null : (
        <li>
          {healthContext.reported_age} years · reported{" "}
          {formatReportedDate(healthContext.age_reported_at)}
          {healthContext.age_refresh_due ? <RefreshNote noun="age" /> : null}
        </li>
      )}
      {healthContext.entered_weight === null ? null : (
        <li>
          {formatDecimal(healthContext.entered_weight)} {healthContext.weight_unit} · reported{" "}
          {formatReportedDate(healthContext.weight_reported_at)}
          {healthContext.weight_refresh_due ? <RefreshNote noun="weight" /> : null}
        </li>
      )}
    </ul>
  );
}

function RefreshNote({ noun }: { noun: string }) {
  return <span className="text-clay"> · This {noun} is worth reporting again when you can.</span>;
}
