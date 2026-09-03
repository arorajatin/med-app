import { useState } from "react";
import { ApiError } from "../../api/client";
import { putSelfProfile } from "../../api/onboarding";
import type { ProfileRead } from "../../api/types";
import { ErrorBanner } from "../../components/ErrorBanner";
import { FormField } from "../../components/FormField";
import { MAX_DISPLAY_NAME_LENGTH, validateDisplayName } from "../validation";

interface SelfProfileStepProps {
  token: string;
  profile: ProfileRead | null;
  onCompleted: () => void;
}

const SEX_OPTIONS = [
  { value: "", label: "Prefer not to say" },
  { value: "female", label: "Female" },
  { value: "male", label: "Male" },
  { value: "other", label: "Other" },
];

export function SelfProfileStep({ token, profile, onCompleted }: SelfProfileStepProps) {
  const [displayName, setDisplayName] = useState(profile?.display_name ?? "");
  const [sex, setSex] = useState(profile?.sex ?? "");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const name = validateDisplayName(displayName);
    if (!name.ok) {
      setFieldError(name.error);
      return;
    }
    setFieldError(null);
    setError(null);
    setSubmitting(true);
    try {
      await putSelfProfile(token, { displayName: name.value, sex: sex === "" ? null : sex });
      onCompleted();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Could not save your profile.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="panel" onSubmit={handleSubmit} noValidate>
      <h2>Your name</h2>
      <p>
        This account has one profile for you, and you can add family profiles later. Resuming
        onboarding updates this profile instead of creating another one.
      </p>
      <ErrorBanner message={error} />
      <FormField
        id="display-name"
        label="Name"
        hint="The name shown on your own profile."
        error={fieldError}
      >
        {(describedBy) => (
          <input
            id="display-name"
            className="input"
            type="text"
            value={displayName}
            maxLength={MAX_DISPLAY_NAME_LENGTH}
            autoComplete="name"
            aria-describedby={describedBy}
            aria-invalid={fieldError ? true : undefined}
            onChange={(event) => setDisplayName(event.target.value)}
          />
        )}
      </FormField>
      <FormField id="sex" label="Sex (optional)">
        {(describedBy) => (
          <select
            id="sex"
            className="input"
            value={sex}
            aria-describedby={describedBy}
            onChange={(event) => setSex(event.target.value)}
          >
            {SEX_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        )}
      </FormField>
      <button className="button" type="submit" disabled={submitting}>
        {submitting ? "Saving…" : "Save and continue"}
      </button>
    </form>
  );
}
