import { useState } from "react";
import { ApiError } from "../../api/client";
import { acceptConsent } from "../../api/onboarding";
import { ErrorBanner } from "../../components/ErrorBanner";
import { CONSENT_POLICY_VERSION, CONSENT_SCOPE } from "../consentPolicy";

interface ConsentStepProps {
  token: string;
  alreadyAccepted: boolean;
  onCompleted: () => void;
}

export function ConsentStep({ token, alreadyAccepted, onCompleted }: ConsentStepProps) {
  const [accepted, setAccepted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!accepted) {
      setError("Tick the box to accept the AI processing terms.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await acceptConsent(token, {
        policyVersion: CONSENT_POLICY_VERSION,
        acceptedScope: CONSENT_SCOPE,
      });
      onCompleted();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Could not record your acceptance.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="panel" onSubmit={handleSubmit} noValidate>
      <h2>AI processing terms</h2>
      <p>
        Every feature in this release depends on AI processing, so acceptance is required to finish
        onboarding.
      </p>
      <ul className="prose-list">
        <li>Documents you upload are sent to an AI provider to extract their contents.</li>
        <li>Facts you have reviewed, and the ones you type yourself, can be used in Chat.</li>
        <li>Nothing is shared with other people; only you can see this account's records.</li>
      </ul>
      <p className="muted">
        Policy version {CONSENT_POLICY_VERSION}. This release has no mode that runs with AI
        processing turned off, and it does not yet offer withdrawal after acceptance.
      </p>
      {alreadyAccepted ? (
        <p className="banner banner--info">
          You have already accepted these terms. Submitting again records a fresh acceptance.
        </p>
      ) : null}
      <ErrorBanner message={error} />
      <label className="checkbox">
        <input
          type="checkbox"
          checked={accepted}
          onChange={(event) => setAccepted(event.target.checked)}
        />
        I accept the AI processing terms for this account.
      </label>
      <button className="button" type="submit" disabled={submitting}>
        {submitting ? "Saving…" : "Accept and continue"}
      </button>
      <p className="muted">
        If you do not accept, onboarding stays incomplete and Upload, Feed, Drive, and Chat remain
        closed.
      </p>
    </form>
  );
}
