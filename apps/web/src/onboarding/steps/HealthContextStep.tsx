import { useState } from "react";
import { ApiError } from "../../api/client";
import { createHealthContext } from "../../api/onboarding";
import type { ProfileHealthContextRead, WeightUnit } from "../../api/types";
import { ErrorBanner } from "../../components/ErrorBanner";
import { FormField } from "../../components/FormField";
import { MAX_AGE, MIN_AGE, validateAge, validateWeight } from "../validation";

interface HealthContextStepProps {
  token: string;
  profileId: string;
  alreadyRecorded: boolean;
  onCompleted: (recorded: ProfileHealthContextRead) => void;
}

export function HealthContextStep({
  token,
  profileId,
  alreadyRecorded,
  onCompleted,
}: HealthContextStepProps) {
  const [age, setAge] = useState("");
  const [weight, setWeight] = useState("");
  const [unit, setUnit] = useState<WeightUnit>("kg");
  const [ageError, setAgeError] = useState<string | null>(null);
  const [weightError, setWeightError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const validAge = validateAge(age);
    const validWeight = validateWeight(weight, unit);
    setAgeError(validAge.ok ? null : validAge.error);
    setWeightError(validWeight.ok ? null : validWeight.error);
    if (!validAge.ok || !validWeight.ok) {
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      // Both values are stamped with the moment they were reported; the backend
      // never ages them on afterwards.
      const recorded = await createHealthContext(token, profileId, {
        reportedAge: validAge.value,
        enteredWeight: validWeight.value.entered,
        weightUnit: validWeight.value.unit,
        reportedAt: new Date().toISOString(),
      });
      onCompleted(recorded);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Could not save your health context.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="panel" onSubmit={handleSubmit} noValidate>
      <h2>Age and weight</h2>
      <p>
        Both values are saved with today's date and are always shown with the date you reported
        them. They are never updated on their own.
      </p>
      {alreadyRecorded ? (
        <p className="banner banner--info">
          You have recorded these before. Saving again adds a newer reported value and keeps the
          earlier one.
        </p>
      ) : null}
      <ErrorBanner message={error} />
      <FormField
        id="reported-age"
        label="Age in years"
        hint={`Whole completed years, ${MIN_AGE} to ${MAX_AGE}.`}
        error={ageError}
      >
        {(describedBy) => (
          <input
            id="reported-age"
            className="input"
            type="text"
            inputMode="numeric"
            value={age}
            aria-describedby={describedBy}
            aria-invalid={ageError ? true : undefined}
            onChange={(event) => setAge(event.target.value)}
          />
        )}
      </FormField>
      <FormField
        id="entered-weight"
        label="Weight"
        hint="Enter the number you know, then pick its unit. It is stored in the unit you chose."
        error={weightError}
      >
        {(describedBy) => (
          <div className="input-row">
            <input
              id="entered-weight"
              className="input"
              type="text"
              inputMode="decimal"
              value={weight}
              aria-describedby={describedBy}
              aria-invalid={weightError ? true : undefined}
              onChange={(event) => setWeight(event.target.value)}
            />
            <select
              className="input input--unit"
              value={unit}
              aria-label="Weight unit"
              onChange={(event) => setUnit(event.target.value as WeightUnit)}
            >
              <option value="kg">kg</option>
              <option value="lb">lb</option>
            </select>
          </div>
        )}
      </FormField>
      <button className="button" type="submit" disabled={submitting}>
        {submitting ? "Saving…" : "Save and continue"}
      </button>
    </form>
  );
}
