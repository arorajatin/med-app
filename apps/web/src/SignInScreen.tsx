import { useState } from "react";
import { signInWithGoogle } from "./auth/session";
import { ErrorBanner } from "./components/ErrorBanner";
import { GoogleMark } from "./components/GoogleMark";

interface SignInScreenProps {
  /** A failure carried back on the redirect, such as a cancelled provider authorization. */
  redirectError: string | null;
}

export function SignInScreen({ redirectError }: SignInScreenProps) {
  const [failure, setFailure] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  async function handleGoogle() {
    setFailure(null);
    setStarting(true);
    try {
      // On success the browser leaves for Google, so nothing after this runs.
      await signInWithGoogle();
    } catch (cause) {
      setFailure(cause instanceof Error ? cause.message : "Could not start Google sign-in.");
      setStarting(false);
    }
  }

  return (
    <section className="panel panel--narrow">
      <h2>Sign in</h2>
      <p>
        Your medical records are private to this account. Signing in with Google confirms your
        email address with Google, so there is no separate password to manage here.
      </p>
      <ErrorBanner message={failure ?? redirectError} />
      <button
        className="button button--google"
        type="button"
        onClick={() => void handleGoogle()}
        disabled={starting}
      >
        <GoogleMark />
        {starting ? "Taking you to Google…" : "Continue with Google"}
      </button>
      <p className="muted">
        We receive your name and email address from Google. We never receive your Google password.
      </p>
      <p className="muted">
        Creating an account authorizes AI processing of the medical records you upload and the
        reviewed personal memory used in Chat.
      </p>
    </section>
  );
}
