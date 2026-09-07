import { useEffect, useState } from "react";
import { ApiError } from "../api/client";
import { getHealthContext, getOnboarding } from "../api/onboarding";
import type { OnboardingRead, OnboardingStep, ProfileHealthContextSummary } from "../api/types";
import { ErrorBanner } from "../components/ErrorBanner";
import { StepIndicator } from "../components/StepIndicator";
import { FamilySpace } from "../family/FamilySpace";
import { SummaryPanel } from "./SummaryPanel";
import { AttestedMemoryStep } from "./steps/AttestedMemoryStep";
import { HealthContextStep } from "./steps/HealthContextStep";
import { SelfProfileStep } from "./steps/SelfProfileStep";

interface OnboardingWizardProps {
  onUnauthenticated: () => void;
}

const LOAD_FAILED = "Could not load your onboarding progress.";

interface LoadedState {
  onboarding: OnboardingRead;
  healthContext: ProfileHealthContextSummary | null;
}

/**
 * Onboarding progress and the recorded age and weight are read together, so a
 * resumed session shows the values already on the profile rather than only the
 * ones entered in this visit.
 */
async function loadState(): Promise<LoadedState> {
  const onboarding = await getOnboarding();
  if (onboarding.self_profile === null) {
    return { onboarding, healthContext: null };
  }
  const healthContext = await getHealthContext(onboarding.self_profile.id);
  return { onboarding, healthContext };
}

export function OnboardingWizard({ onUnauthenticated }: OnboardingWizardProps) {
  const [onboarding, setOnboarding] = useState<OnboardingRead | null>(null);
  const [activeStep, setActiveStep] = useState<OnboardingStep | null>(null);
  const [reviewing, setReviewing] = useState(false);
  const [healthContext, setHealthContext] = useState<ProfileHealthContextSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    loadState()
      .then((loaded) => {
        if (cancelled) {
          return;
        }
        setOnboarding(loaded.onboarding);
        setHealthContext(loaded.healthContext);
        setError(null);
        // A resumed session opens at the first step the account has not finished.
        setActiveStep(loaded.onboarding.next_step);
        setReviewing(false);
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
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [onUnauthenticated]);

  async function handleStepCompleted() {
    let loaded: LoadedState;
    try {
      loaded = await loadState();
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) {
        onUnauthenticated();
        return;
      }
      setError(cause instanceof ApiError ? cause.message : LOAD_FAILED);
      return;
    }
    const state = loaded.onboarding;
    setOnboarding(state);
    setHealthContext(loaded.healthContext);
    setError(null);
    // Only a completed onboarding can return to its summary. If later required
    // steps remain, correcting an earlier answer resumes at the first one.
    setActiveStep(reviewing && state.status === "completed" ? null : state.next_step);
    setReviewing(false);
  }

  function handleEditStep(step: OnboardingStep) {
    setActiveStep(step);
    setReviewing(true);
  }

  function renderStep(state: OnboardingRead) {
    const profile = state.self_profile;
    const completed = state.completed_steps;

    if (activeStep === null) {
      return (
        <SummaryPanel
          onboarding={state}
          healthContext={healthContext}
          onEditStep={handleEditStep}
        />
      );
    }
    if (activeStep === "self_profile") {
      return <SelfProfileStep profile={profile} onCompleted={handleStepCompleted} />;
    }
    if (profile === null) {
      return <ErrorBanner message="Add your own profile before recording health details." />;
    }
    if (activeStep === "health_context") {
      return (
        <HealthContextStep
          profileId={profile.id}
          recorded={completed.includes("health_context") ? healthContext : null}
          onCompleted={handleStepCompleted}
        />
      );
    }
    return (
      <AttestedMemoryStep
        key={activeStep}
        profileId={profile.id}
        category={activeStep === "conditions" ? "condition" : "medication"}
        onCompleted={handleStepCompleted}
      />
    );
  }

  if (loading) {
    return <p className="muted">Loading your onboarding progress…</p>;
  }
  if (onboarding === null) {
    return <ErrorBanner message={error ?? LOAD_FAILED} />;
  }

  return (
    <div className="wizard">
      <StepIndicator
        completedSteps={onboarding.completed_steps}
        activeStep={activeStep}
        onSelectStep={handleEditStep}
      />
      <ErrorBanner message={error} />
      {renderStep(onboarding)}
      {onboarding.status === "completed" && activeStep === null ? (
        <FamilySpace onUnauthenticated={onUnauthenticated} />
      ) : null}
      {activeStep !== null && reviewing ? (
        <button
          className="button button--quiet"
          type="button"
          onClick={() => {
            setActiveStep(onboarding.status === "completed" ? null : onboarding.next_step);
            setReviewing(false);
          }}
        >
          {onboarding.status === "completed" ? "Back to summary" : "Back to current step"}
        </button>
      ) : null}
    </div>
  );
}
