import { useCallback, useEffect, useState } from "react";
import { SignInScreen } from "./SignInScreen";
import { setAccessTokenProvider } from "./api/client";
import {
  type AccountSession,
  clearAuthRedirectError,
  currentAccessToken,
  isAuthConfigured,
  onSessionChange,
  readAuthRedirectError,
  signOut,
} from "./auth/session";
import { ErrorBanner } from "./components/ErrorBanner";
import { EntryLayout } from "./navigation/EntryLayout";
import { OnboardingWizard } from "./onboarding/OnboardingWizard";

export function App() {
  const [session, setSession] = useState<AccountSession | null>(null);
  const [restored, setRestored] = useState(false);
  // How the app was entered is fixed by the time it renders, so read it once
  // rather than synchronize it.
  const [redirectError, setRedirectError] = useState<string | null>(readAuthRedirectError);

  useEffect(() => {
    // Every request asks the authentication client for a current token.
    setAccessTokenProvider(currentAccessToken);
    // Keep a failed redirect out of the address bar so a reload starts clean.
    clearAuthRedirectError();

    return onSessionChange((next) => {
      setSession(next);
      setRestored(true);
      if (next !== null) {
        setRedirectError(null);
      }
    });
  }, []);

  // Stable so the wizard's load effect does not re-run on every render.
  const handleSignOut = useCallback(() => {
    void signOut();
  }, []);

  if (!isAuthConfigured) {
    return (
      <EntryLayout>
        <section className="panel">
          <h2>Almost there</h2>
          <ErrorBanner message="Sign-in is not configured for this build. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY, then reload." />
        </section>
      </EntryLayout>
    );
  }
  if (!restored) {
    return (
      <EntryLayout>
        <section className="panel items-center text-center">
          <span className="border-sage/40 border-t-sage h-9 w-9 animate-spin rounded-full border-2" />
          <p className="muted">Restoring your session…</p>
        </section>
      </EntryLayout>
    );
  }
  if (session === null) {
    return (
      <EntryLayout>
        <SignInScreen redirectError={redirectError} />
      </EntryLayout>
    );
  }
  return (
    <OnboardingWizard
      key={session.userId}
      email={session.email}
      onSignOut={handleSignOut}
      onUnauthenticated={handleSignOut}
    />
  );
}
