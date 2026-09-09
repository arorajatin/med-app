/**
 * FamCare's mark: a house whose walls hold a heart. The house says the records
 * live somewhere settled; the heart says whose they are.
 */
export function BrandMark({ className = "h-9 w-9" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M3.6 10.2 12 3.4l8.4 6.8V19a1.8 1.8 0 0 1-1.8 1.8H5.4A1.8 1.8 0 0 1 3.6 19Z"
        className="fill-sage-soft stroke-sage"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="M12 17.6c-2.4-1.6-3.6-2.8-3.6-4.3a2 2 0 0 1 3.6-1.2 2 2 0 0 1 3.6 1.2c0 1.5-1.2 2.7-3.6 4.3Z"
        className="fill-clay"
      />
    </svg>
  );
}

/**
 * The mark beside the name. `as` lets a page make this its own heading without
 * a second visible title.
 */
export function Wordmark({
  size = "medium",
  tagline = false,
}: {
  size?: "small" | "medium";
  tagline?: boolean;
}) {
  const mark = size === "small" ? "h-8 w-8" : "h-10 w-10";
  const name = size === "small" ? "text-xl" : "text-2xl";
  return (
    <span className="flex items-center gap-2.5">
      <BrandMark className={mark} />
      <span className="flex flex-col">
        <span className={`font-display font-semibold tracking-tight ${name}`}>
          Fam<span className="text-sage">Care</span>
        </span>
        {tagline ? (
          <span className="text-ink-soft text-xs">A home for your family’s health</span>
        ) : null}
      </span>
    </span>
  );
}
