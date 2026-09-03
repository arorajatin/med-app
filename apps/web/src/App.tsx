import { useCallback, useState } from "react";
import { SignInPanel } from "./SignInPanel";
import { OnboardingWizard } from "./onboarding/OnboardingWizard";
import { clearStoredToken, readStoredToken, storeToken } from "./session";

export function App() {
  const [token, setToken] = useState<string | null>(() => readStoredToken());

  function handleSignedIn(value: string) {
    storeToken(value);
    setToken(value);
  }

  // Stable so the wizard's load effect does not re-run on every render.
  const handleSignOut = useCallback(() => {
    clearStoredToken();
    setToken(null);
  }, []);

  return (
    <div className="app">
      <header className="app__header">
        <div>
          <p className="app__eyebrow">Family Health</p>
          <h1>Set up your account</h1>
        </div>
        {token === null ? null : (
          <button className="button button--quiet" type="button" onClick={handleSignOut}>
            Sign out
          </button>
        )}
      </header>
      <main>
        {token === null ? (
          <SignInPanel onSignedIn={handleSignedIn} />
        ) : (
          <OnboardingWizard key={token} token={token} onUnauthenticated={handleSignOut} />
        )}
      </main>
    </div>
  );
}
