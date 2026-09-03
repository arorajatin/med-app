import { useState } from "react";
import { ApiError } from "./api/client";
import { getAccount } from "./api/onboarding";
import { ErrorBanner } from "./components/ErrorBanner";
import { FormField } from "./components/FormField";

interface SignInPanelProps {
  onSignedIn: (token: string) => void;
}

/**
 * Registration, Google sign-in, and email verification are still backend work
 * (task 2.3). Until they land, the client takes the bearer token the API
 * expects: a user id in local development, a Supabase access token otherwise.
 */
export function SignInPanel({ onSignedIn }: SignInPanelProps) {
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const value = token.trim();
    if (value === "") {
      setError("Enter the token the API should use for you.");
      return;
    }
    setError(null);
    setChecking(true);
    try {
      await getAccount(value);
      onSignedIn(value);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Could not reach the API.");
    } finally {
      setChecking(false);
    }
  }

  return (
    <form className="panel" onSubmit={handleSubmit} noValidate>
      <h2>Sign in</h2>
      <p>
        This client sends <code>Authorization: Bearer &lt;token&gt;</code>. With{" "}
        <code>DEV_AUTH_ENABLED=true</code> the token is any user id you choose, and each id gets its
        own account.
      </p>
      <ErrorBanner message={error} />
      <FormField id="token" label="User id or access token">
        {(describedBy) => (
          <input
            id="token"
            className="input"
            type="text"
            value={token}
            autoComplete="off"
            aria-describedby={describedBy}
            onChange={(event) => setToken(event.target.value)}
          />
        )}
      </FormField>
      <button className="button" type="submit" disabled={checking}>
        {checking ? "Checking…" : "Continue"}
      </button>
    </form>
  );
}
