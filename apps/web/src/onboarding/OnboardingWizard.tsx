import { useEffect, useState } from "react";
import { ApiError } from "../api/client";
import { getOnboarding } from "../api/onboarding";
import type { OnboardingRead, OnboardingStep, ProfileHealthContextRead } from "../api/types";
import { ErrorBanner } from "../components/ErrorBanner";
import { StepIndicator } from "../components/StepIndicator";
import { SummaryPanel } from "./SummaryPanel";
import { AttestedMemoryStep } from "./steps/AttestedMemoryStep";
import { ConsentStep } from "./steps/ConsentStep";
import { HealthContextStep } from "./steps/HealthContextStep";
import { SelfProfileStep } from "./steps/SelfProfileStep";

interface OnboardingWizardProps {
  onUnauthenticated: () => void;
}

const LOAD_FAILED = "Could not load your onboarding progress.";

export function OnboardingWizard({ onUnauthenticated }: OnboardingWizardProps) {
  const [onboarding, setOnboarding] = useState<OnboardingRead | null>(null);
  const [activeStep, setActiveStep] = useState<OnboardingStep | null>(null);
  const [reviewing, setReviewing] = useState(false);
  const [healthContext, setHealthContext] = useState<ProfileHealthContextRead | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getOnboarding()
      .then((state) => {
        if (cancelled) {
          return;
        }
        setOnboarding(state);
        setError(null);
        // A resumed session opens at the first step the account has not finished.
        setActiveStep(state.next_step);
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
    let state: OnboardingRead;
    try {
      state = await getOnboarding();
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) {
        onUnauthenticated();
        return;
      }
      setError(cause instanceof ApiError ? cause.message : LOAD_FAILED);
      return;
    }
    setOnboarding(state);
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
    if (activeStep === "consent") {
      return (
        <ConsentStep
          alreadyAccepted={completed.includes("consent")}
          onCompleted={handleStepCompleted}
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
          alreadyRecorded={completed.includes("health_context")}
          onCompleted={(recorded) => {
            setHealthContext(recorded);
            void handleStepCompleted();
          }}
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
