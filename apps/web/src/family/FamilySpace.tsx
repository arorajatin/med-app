import { useEffect, useState } from "react";
import { ApiError } from "../api/client";
import { listProfiles } from "../api/profiles";
import type { ProfileRead } from "../api/types";
import { ErrorBanner } from "../components/ErrorBanner";
import { AddFamilyMemberForm } from "./AddFamilyMemberForm";

interface FamilySpaceProps {
  onUnauthenticated: () => void;
}

const LOAD_FAILED = "Could not load your family profiles.";

/**
 * The account's family space. One authenticated person manages every profile in
 * the first release, so a profile here is a medical context, not a login.
 */
export function FamilySpace({ onUnauthenticated }: FamilySpaceProps) {
  const [profiles, setProfiles] = useState<ProfileRead[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  // Bumped after a profile is added, so the list is re-read from the service
  // rather than guessed at from the response.
  const [reloadCount, setReloadCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    listProfiles()
      .then((loaded) => {
        if (cancelled) {
          return;
        }
        setProfiles(loaded);
        setError(null);
      })
      .catch((cause: unknown) => {
        if (cancelled) {
          return;
        }
        if (cause instanceof ApiError && cause.status === 401) {
          onUnauthenticated();
          return;
        }
        setError(cause instanceof ApiError ? cause.message : LOAD_FAILED);
      });
    return () => {
      cancelled = true;
    };
  }, [onUnauthenticated, reloadCount]);

  function handleAdded() {
    setAdding(false);
    setReloadCount((count) => count + 1);
  }

  return (
    <section className="panel">
      <h2>Your family</h2>
      <p>
        Everyone here is managed from your account. Family members do not sign in themselves in this
        release.
      </p>
      <ErrorBanner message={error} />
      {profiles === null ? (
        <p className="muted">Loading your family profiles…</p>
      ) : (
        <ul className="entry-list" aria-label="Family profiles">
          {profiles.map((profile) => (
            <li className="entry-list__item" key={profile.id}>
              <span>{profile.display_name}</span>
              <span className="muted">
                {profile.relationship === "self" ? "You" : profile.relationship}
                {profile.sex ? ` · ${profile.sex}` : ""}
              </span>
            </li>
          ))}
        </ul>
      )}
      {adding ? (
        <AddFamilyMemberForm onAdded={handleAdded} onCancel={() => setAdding(false)} />
      ) : (
        <button className="button" type="button" onClick={() => setAdding(true)}>
          Add a family member
        </button>
      )}
    </section>
  );
}
