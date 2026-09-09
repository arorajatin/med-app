/**
 * Warm background tones for family avatars. The tone follows from the name, so
 * a person keeps the same colour everywhere without any stored preference.
 */
const TONES = [
  "bg-sage-soft ring-sage/30",
  "bg-clay-soft ring-clay/30",
  "bg-honey-soft ring-honey/35",
  "bg-plum-soft ring-plum/30",
] as const;

const SIZES = {
  small: "h-9 w-9 text-sm",
  medium: "h-11 w-11 text-base",
  large: "h-14 w-14 text-lg",
} as const;

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const first = parts[0]?.[0] ?? "?";
  const last = parts.length > 1 ? (parts[parts.length - 1]?.[0] ?? "") : "";
  return (first + last).toUpperCase();
}

function tone(name: string): string {
  let sum = 0;
  for (const character of name) {
    sum += character.codePointAt(0) ?? 0;
  }
  return TONES[sum % TONES.length] ?? TONES[0];
}

/** A person's initials in a soft circle. Decorative: the name is always nearby. */
export function Avatar({
  name,
  size = "medium",
}: {
  name: string;
  size?: keyof typeof SIZES;
}) {
  return (
    <span
      aria-hidden="true"
      className={`text-ink flex flex-none items-center justify-center rounded-full font-display font-semibold ring-1 ${tone(name)} ${SIZES[size]}`}
    >
      {initials(name)}
    </span>
  );
}
