/**
 * Read an optional build-time setting.
 *
 * A variable that is present but empty, which is how an unfilled line in a
 * `.env` file arrives, means "not set". Nullish coalescing alone would keep the
 * empty string and quietly break whatever depends on it.
 */
export function readOptionalEnv(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}
