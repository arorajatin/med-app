const STORAGE_KEY = "med-app.session-token";

/**
 * The backend reads `Authorization: Bearer <token>`. With `DEV_AUTH_ENABLED=true`
 * the token is simply the user id; otherwise it is a Supabase access token.
 */
export function readStoredToken(): string | null {
  try {
    const token = window.localStorage.getItem(STORAGE_KEY);
    return token && token.trim() !== "" ? token : null;
  } catch {
    return null;
  }
}

export function storeToken(token: string): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, token);
  } catch {
    // A blocked storage API only costs the person a re-entry on reload.
  }
}

export function clearStoredToken(): void {
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Nothing to clean up when storage is unavailable.
  }
}
