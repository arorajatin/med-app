import type { Session } from "@supabase/supabase-js";
import { isAuthConfigured, requireSupabase } from "./supabaseClient";

export { isAuthConfigured };

export interface AccountSession {
  userId: string;
  email: string | null;
}

/** Query parameters an identity provider adds when a redirect sign-in fails. */
const ERROR_PARAMS = ["error", "error_code", "error_description"];

function toAccountSession(session: Session | null): AccountSession | null {
  if (session === null) {
    return null;
  }
  return { userId: session.user.id, email: session.user.email ?? null };
}

/**
 * Read the access token for each request rather than holding one.
 *
 * Supabase rotates the access token roughly hourly and refreshes it in the
 * background. A token captured when a screen rendered can therefore be expired
 * by the time someone submits that screen.
 */
export async function currentAccessToken(): Promise<string | null> {
  if (!isAuthConfigured) {
    return null;
  }
  const { data } = await requireSupabase().auth.getSession();
  return data.session?.access_token ?? null;
}

/** Subscribe to sign-in state. The listener is called with the current session first. */
export function onSessionChange(listener: (session: AccountSession | null) => void): () => void {
  if (!isAuthConfigured) {
    listener(null);
    return () => {};
  }
  const { data } = requireSupabase().auth.onAuthStateChange((_event, session) => {
    listener(toAccountSession(session));
  });
  return () => data.subscription.unsubscribe();
}

export async function signInWithGoogle(): Promise<void> {
  const { error } = await requireSupabase().auth.signInWithOAuth({
    provider: "google",
    options: { redirectTo: window.location.origin },
  });
  if (error !== null) {
    throw new Error(error.message);
  }
}

export async function signOut(): Promise<void> {
  if (!isAuthConfigured) {
    return;
  }
  await requireSupabase().auth.signOut();
}

/**
 * A cancelled or rejected sign-in comes back as parameters on the redirect
 * rather than as a thrown error, because the browser left the app to visit the
 * provider.
 */
export function readAuthRedirectError(): string | null {
  const search = new URLSearchParams(window.location.search);
  const hash = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  const description = search.get("error_description") ?? hash.get("error_description");
  if (description !== null && description.trim() !== "") {
    return description;
  }
  const code = search.get("error") ?? hash.get("error");
  if (code !== null && code.trim() !== "") {
    return `Sign-in did not complete (${code}).`;
  }
  return null;
}

/**
 * Drop only the error parameters. The authorization code is left alone because
 * the Supabase client consumes it and cleans the URL once the exchange succeeds.
 */
export function clearAuthRedirectError(): void {
  const url = new URL(window.location.href);
  let changed = false;
  for (const key of ERROR_PARAMS) {
    if (url.searchParams.has(key)) {
      url.searchParams.delete(key);
      changed = true;
    }
  }
  if (url.hash !== "" && /(?:^|[#&])error=/.test(url.hash)) {
    url.hash = "";
    changed = true;
  }
  if (changed) {
    window.history.replaceState({}, "", url.toString());
  }
}
