import { useEffect, useState } from "react";
import { ApiError } from "../api/client";
import { listProfiles } from "../api/profiles";
import type { ProfileRead } from "../api/types";
import { Avatar } from "../components/Avatar";
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
      <div>
        <h2>Your family</h2>
        <p className="muted mt-1.5">
          Everyone here is managed from your account. Family members do not sign in themselves in
          this release.
        </p>
      </div>
      <ErrorBanner message={error} />
      {profiles === null ? (
        <p className="muted">Loading your family profiles…</p>
      ) : (
        <ul className="grid gap-2 sm:grid-cols-2" aria-label="Family profiles">
          {profiles.map((profile) => (
            <li
              className="border-line bg-surface-sunk/60 flex items-center gap-3 rounded-2xl border p-3"
              key={profile.id}
            >
              <Avatar name={profile.display_name} />
              <span className="flex min-w-0 flex-col">
                <span className="truncate font-semibold">{profile.display_name}</span>
                <span className="muted truncate text-sm capitalize">
                  {profile.relationship === "self" ? "You" : profile.relationship}
                  {profile.sex ? ` · ${profile.sex}` : ""}
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
      {adding ? (
        <AddFamilyMemberForm onAdded={handleAdded} onCancel={() => setAdding(false)} />
      ) : (
        <button className="button" type="button" onClick={() => setAdding(true)}>
          <span aria-hidden="true" className="text-lg leading-none">
            +
          </span>
          Add a family member
        </button>
      )}
    </section>
  );
}
