import { useEffect, useState } from "react";
import { ApiError } from "../../api/client";
import { declareAttestedMemory, getMemory } from "../../api/onboarding";
import type { AttestedCategory } from "../../api/types";
import { ErrorBanner } from "../../components/ErrorBanner";
import { attestedTitles } from "../attestedMemory";
import { MAX_ATTESTED_TITLE_LENGTH, validateAttestedEntries } from "../validation";

interface AttestedMemoryStepProps {
  profileId: string;
  category: AttestedCategory;
  onCompleted: () => void;
}

interface Copy {
  heading: string;
  noun: string;
  intro: string;
  placeholder: string;
  none: string;
}

const COPY: Record<AttestedCategory, Copy> = {
  condition: {
    heading: "Current conditions",
    noun: "condition",
    intro:
      "List the conditions you live with right now, in your own words. What you type here is trusted straight away, because you reported it yourself.",
    placeholder: "For example: Asthma",
    none: "I have no current conditions to report.",
  },
  medication: {
    heading: "Current medications",
    noun: "medication",
    intro:
      "List the medications you take right now, in your own words. What you type here is trusted straight away, because you reported it yourself.",
    placeholder: "For example: Salbutamol inhaler, as needed",
    none: "I take no medications right now.",
  },
};

export function AttestedMemoryStep({
  profileId,
  category,
  onCompleted,
}: AttestedMemoryStepProps) {
  const copy = COPY[category];
  const [titles, setTitles] = useState<string[]>([""]);
  const [declaredNone, setDeclaredNone] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getMemory(profileId)
      .then((memory) => {
        if (cancelled) {
          return;
        }
        const existing = attestedTitles(memory.facts, category);
        setTitles(existing.length > 0 ? existing : [""]);
      })
      .catch(() => {
        // Prefilling is a convenience; an empty form is still correct.
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [profileId, category]);

  function updateTitle(index: number, value: string) {
    setTitles((current) => current.map((title, position) => (position === index ? value : title)));
  }

  function removeTitle(index: number) {
    setTitles((current) => {
      const remaining = current.filter((_, position) => position !== index);
      return remaining.length > 0 ? remaining : [""];
    });
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const entries = validateAttestedEntries(titles, declaredNone, copy.noun);
    if (!entries.ok) {
      setError(entries.error);
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      // The list is the complete current set; an empty list is a real answer.
      await declareAttestedMemory(
        profileId,
        category,
        entries.value.map((title) => ({ title })),
      );
      onCompleted();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : `Could not save your ${copy.noun}s.`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="panel" onSubmit={handleSubmit} noValidate>
      <h2>{copy.heading}</h2>
      <p>{copy.intro}</p>
      <ErrorBanner message={error} />
      {loading ? <p className="muted">Loading what you saved before…</p> : null}
      <ul className="entry-list">
        {titles.map((title, index) => (
          <li className="entry-list__item" key={index}>
            <label className="visually-hidden" htmlFor={`${category}-${index}`}>
              {`${copy.heading} ${index + 1}`}
            </label>
            <input
              id={`${category}-${index}`}
              className="input"
              type="text"
              value={title}
              disabled={declaredNone}
              maxLength={MAX_ATTESTED_TITLE_LENGTH}
              placeholder={copy.placeholder}
              onChange={(event) => updateTitle(index, event.target.value)}
            />
            <button
              className="button button--quiet"
              type="button"
              disabled={declaredNone}
              onClick={() => removeTitle(index)}
            >
              Remove
            </button>
          </li>
        ))}
      </ul>
      <button
        className="button button--quiet"
        type="button"
        disabled={declaredNone}
        onClick={() => setTitles((current) => [...current, ""])}
      >
        Add another
      </button>
      <label className="checkbox">
        <input
          type="checkbox"
          checked={declaredNone}
          onChange={(event) => setDeclaredNone(event.target.checked)}
        />
        {copy.none}
      </label>
      <button className="button" type="submit" disabled={submitting}>
        {submitting ? "Saving…" : "Save and continue"}
      </button>
    </form>
  );
}
