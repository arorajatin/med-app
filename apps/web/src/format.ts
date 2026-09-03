/** Age and weight are always shown with the date they were reported. */
export function formatReportedDate(iso: string | null): string {
  if (iso === null) {
    return "date unknown";
  }
  const parsed = new Date(withTimeZone(iso));
  if (Number.isNaN(parsed.getTime())) {
    return "date unknown";
  }
  return parsed.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/**
 * The API returns some timestamps without an offset. Those are UTC, so say so
 * rather than let the browser read them as local time and shift the date.
 */
function withTimeZone(iso: string): string {
  return /(?:Z|[+-]\d{2}:?\d{2})$/.test(iso) ? iso : `${iso}Z`;
}

/** The API returns exact decimals such as "61.50000000"; show what was typed. */
export function formatDecimal(value: string | null): string {
  if (value === null) {
    return "";
  }
  return value.includes(".") ? value.replace(/\.?0+$/, "") : value;
}
