import { useState } from "react";
import { ApiError } from "../api/client";
import { createProfile } from "../api/profiles";
import { ErrorBanner } from "../components/ErrorBanner";
import { FormField } from "../components/FormField";
import {
  MAX_DISPLAY_NAME_LENGTH,
  MAX_RELATIONSHIP_LENGTH,
  validateDisplayName,
  validateRelationship,
} from "../onboarding/validation";

interface AddFamilyMemberFormProps {
  onAdded: () => void;
  onCancel: () => void;
}

const SEX_OPTIONS = [
  { value: "", label: "Prefer not to say" },
  { value: "female", label: "Female" },
  { value: "male", label: "Male" },
  { value: "other", label: "Other" },
];

export function AddFamilyMemberForm({ onAdded, onCancel }: AddFamilyMemberFormProps) {
  const [displayName, setDisplayName] = useState("");
  const [relationship, setRelationship] = useState("");
  const [sex, setSex] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);
  const [relationshipError, setRelationshipError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const name = validateDisplayName(displayName);
    const relation = validateRelationship(relationship);
    setNameError(name.ok ? null : name.error);
    setRelationshipError(relation.ok ? null : relation.error);
    if (!name.ok || !relation.ok) {
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await createProfile({
        displayName: name.value,
        relationship: relation.value,
        sex: sex === "" ? null : sex,
      });
      onAdded();
    } catch (cause) {
      // The service is the authority, including on the one `self` profile rule.
      setError(cause instanceof ApiError ? cause.message : "Could not add this family member.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      className="border-line bg-surface-sunk/60 flex flex-col gap-4 rounded-2xl border p-4 sm:p-5"
      onSubmit={handleSubmit}
      noValidate
      aria-label="Add a family member"
    >
      <h3 className="text-lg">Add a family member</h3>
      <ErrorBanner message={error} />
      <FormField
        id="family-name"
        label="Name"
        hint="The name shown on their profile."
        error={nameError}
      >
        {(describedBy) => (
          <input
            id="family-name"
            className="input"
            type="text"
            value={displayName}
            maxLength={MAX_DISPLAY_NAME_LENGTH}
            aria-describedby={describedBy}
            aria-invalid={nameError ? true : undefined}
            onChange={(event) => setDisplayName(event.target.value)}
          />
        )}
      </FormField>
      <FormField
        id="family-relationship"
        label="Relationship to you"
        hint="For example mother, father, or daughter."
        error={relationshipError}
      >
        {(describedBy) => (
          <input
            id="family-relationship"
            className="input"
            type="text"
            value={relationship}
            maxLength={MAX_RELATIONSHIP_LENGTH}
            aria-describedby={describedBy}
            aria-invalid={relationshipError ? true : undefined}
            onChange={(event) => setRelationship(event.target.value)}
          />
        )}
      </FormField>
      <FormField id="family-sex" label="Sex (optional)">
        {(describedBy) => (
          <select
            id="family-sex"
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
      <div className="flex flex-wrap gap-2.5">
        <button className="button" type="submit" disabled={submitting}>
          {submitting ? "Adding…" : "Add family member"}
        </button>
        <button className="button button--quiet" type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
