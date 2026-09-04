import { useEffect, useState } from "react";
import { getMemory } from "../api/onboarding";
import type {
  AttestedCategory,
  OnboardingRead,
  ProfileHealthContextRead,
  ProfileRead,
} from "../api/types";
import { formatDecimal, formatReportedDate } from "../format";
import { attestedTitles } from "./attestedMemory";
import { STEP_LABELS } from "./steps";
import type { OnboardingStep } from "../api/types";

interface SummaryPanelProps {
  onboarding: OnboardingRead;
  healthContext: ProfileHealthContextRead | null;
  onEditStep: (step: OnboardingStep) => void;
}

export function SummaryPanel({
  onboarding,
  healthContext,
  onEditStep,
}: SummaryPanelProps) {
  const profile = onboarding.self_profile;
  const [attested, setAttested] = useState<Record<AttestedCategory, string[]> | null>(null);

  useEffect(() => {
    if (profile === null) {
      return;
    }
    let cancelled = false;
    getMemory(profile.id)
      .then((memory) => {
        if (cancelled) {
          return;
        }
        setAttested({
          condition: attestedTitles(memory.facts, "condition"),
          medication: attestedTitles(memory.facts, "medication"),
        });
      })
      .catch(() => {
        // The summary still shows everything the onboarding state carries.
      });
    return () => {
      cancelled = true;
    };
  }, [profile]);

  return (
    <section className="panel">
      <h2>Onboarding complete</h2>
      <p>Your account is set up.</p>

      <SummaryRow
        step="self_profile"
        value={<ProfileSummary profile={profile} />}
        onEditStep={onEditStep}
      />
      <SummaryRow
        step="health_context"
        value={<HealthContextSummary healthContext={healthContext} />}
        onEditStep={onEditStep}
      />
      <SummaryRow
        step="conditions"
        value={<AttestedSummary titles={attested?.condition} noun="conditions" />}
        onEditStep={onEditStep}
      />
      <SummaryRow
        step="medications"
        value={<AttestedSummary titles={attested?.medication} noun="medications" />}
        onEditStep={onEditStep}
      />
    </section>
  );
}

interface SummaryRowProps {
  step: OnboardingStep;
  value: React.ReactNode;
  onEditStep: (step: OnboardingStep) => void;
}

function SummaryRow({ step, value, onEditStep }: SummaryRowProps) {
  return (
    <div className="summary-row">
      <div>
        <h3 className="summary-row__title">{STEP_LABELS[step]}</h3>
        <div className="summary-row__value">{value}</div>
      </div>
      <button className="button button--quiet" type="button" onClick={() => onEditStep(step)}>
        Change
      </button>
    </div>
  );
}

function ProfileSummary({ profile }: { profile: ProfileRead | null }) {
  if (profile === null) {
    return <span className="muted">Not recorded yet.</span>;
  }
  return (
    <span>
      {profile.display_name}
      {profile.sex ? ` · ${profile.sex}` : ""}
    </span>
  );
}

function HealthContextSummary({
  healthContext,
}: {
  healthContext: ProfileHealthContextRead | null;
}) {
  if (healthContext === null) {
    return (
      <span className="muted">
        Recorded earlier in this account. Choose Change to report today's age and weight again.
      </span>
    );
  }
  return (
    <ul className="prose-list">
      <li>
        {healthContext.reported_age} years · reported {formatReportedDate(healthContext.age_reported_at)}
      </li>
      <li>
        {formatDecimal(healthContext.entered_weight)} {healthContext.weight_unit} · reported{" "}
        {formatReportedDate(healthContext.weight_reported_at)}
      </li>
    </ul>
  );
}

function AttestedSummary({ titles, noun }: { titles: string[] | undefined; noun: string }) {
  if (titles === undefined) {
    return <span className="muted">Loading…</span>;
  }
  if (titles.length === 0) {
    return <span>You reported no current {noun}.</span>;
  }
  return (
    <ul className="prose-list">
      {titles.map((title) => (
        <li key={title}>{title}</li>
      ))}
    </ul>
  );
}
