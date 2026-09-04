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

  return (
    <div className="app">
      <header className="app__header">
        <div>
          <p className="app__eyebrow">Family Health</p>
          <h1>Set up your account</h1>
        </div>
        {session === null ? null : (
          <div className="app__account">
            {session.email === null ? null : <span className="muted">{session.email}</span>}
            <button className="button button--quiet" type="button" onClick={handleSignOut}>
              Sign out
            </button>
          </div>
        )}
      </header>
      <main>{renderMain()}</main>
    </div>
  );

  function renderMain() {
    if (!isAuthConfigured) {
      return (
        <ErrorBanner message="Sign-in is not configured for this build. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY, then reload." />
      );
    }
    if (!restored) {
      return <p className="muted">Restoring your session…</p>;
    }
    if (session === null) {
      return <SignInScreen redirectError={redirectError} />;
    }
    return (
      <OnboardingWizard key={session.userId} onUnauthenticated={handleSignOut} />
    );
  }
}
