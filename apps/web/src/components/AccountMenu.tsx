import { Avatar } from "./Avatar";
import { ThemeToggle } from "./ThemeToggle";

interface AccountMenuProps {
  /** Null when the provider gave no address, which is rare but allowed. */
  email: string | null;
  onSignOut: () => void;
}

/**
 * Who is signed in, and the way out. Rendered once per layout so there is only
 * ever one "Sign out" control on the page.
 */
export function AccountMenu({ email, onSignOut }: AccountMenuProps) {
  return (
    <div className="flex items-center gap-2 sm:gap-3">
      {email === null ? null : (
        <span className="flex min-w-0 items-center gap-2.5">
          <Avatar name={email} size="small" />
          <span className="text-ink-soft hidden max-w-[16rem] truncate text-sm sm:inline">
            {email}
          </span>
        </span>
      )}
      <ThemeToggle />
      <button
        className="button button--quiet min-h-0 px-3.5 py-2 text-sm"
        type="button"
        onClick={onSignOut}
      >
        Sign out
      </button>
    </div>
  );
}
