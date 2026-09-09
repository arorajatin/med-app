import { useEffect, useState, type ReactNode } from "react";
import { ApiError } from "../api/client";
import { getHealthContext, getOnboarding } from "../api/onboarding";
import type { OnboardingRead, OnboardingStep, ProfileHealthContextSummary } from "../api/types";
import { AccountMenu } from "../components/AccountMenu";
import { Wordmark } from "../components/BrandMark";
import { ErrorBanner } from "../components/ErrorBanner";
import { StepIndicator } from "../components/StepIndicator";
import { FamilySpace } from "../family/FamilySpace";
import { AppShell } from "../navigation/AppShell";
import { SummaryPanel } from "./SummaryPanel";
import { AttestedMemoryStep } from "./steps/AttestedMemoryStep";
import { HealthContextStep } from "./steps/HealthContextStep";
import { SelfProfileStep } from "./steps/SelfProfileStep";

interface OnboardingWizardProps {
  /** The signed-in address, shown in the chrome around every state. */
  email: string | null;
  onSignOut: () => void;
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

export function OnboardingWizard({ email, onSignOut, onUnauthenticated }: OnboardingWizardProps) {
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
    return (
      <SetUpFrame email={email} onSignOut={onSignOut}>
        <p className="muted">Loading your onboarding progress…</p>
      </SetUpFrame>
    );
  }
  if (onboarding === null) {
    return (
      <SetUpFrame email={email} onSignOut={onSignOut}>
        <ErrorBanner message={error ?? LOAD_FAILED} />
      </SetUpFrame>
    );
  }

  const wizard = (
    <div className="flex flex-col gap-5">
      {onboarding.status === "completed" ? null : (
        <StepIndicator
          completedSteps={onboarding.completed_steps}
          activeStep={activeStep}
          onSelectStep={handleEditStep}
        />
      )}
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
  return onboarding.status === "completed" ? (
    <AppShell
      profile={wizard}
      email={email}
      onSignOut={onSignOut}
      onUnauthenticated={onUnauthenticated}
    />
  ) : (
    <SetUpFrame email={email} onSignOut={onSignOut}>
      {wizard}
    </SetUpFrame>
  );
}

/**
 * The chrome around setting up. Onboarding is the first thing anyone sees of
 * FamCare, so it carries the brand rather than looking like a bare form.
 */
function SetUpFrame({
  email,
  onSignOut,
  children,
}: {
  email: string | null;
  onSignOut: () => void;
  children: ReactNode;
}) {
  return (
    <div className="bg-canvas min-h-dvh">
      <header className="border-line bg-canvas/85 sticky top-0 z-10 border-b backdrop-blur-md">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <Wordmark size="small" />
          <AccountMenu email={email} onSignOut={onSignOut} />
        </div>
      </header>
      <main className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6 sm:py-12">
        <div className="mb-7">
          <p className="eyebrow">Settling in</p>
          <h1 className="mt-2 text-3xl sm:text-[2.5rem]">Let’s set up your home</h1>
          <p className="muted mt-2.5 max-w-xl">
            A few details about you first. Everything you add here stays private to this
            account, and you can change any of it later.
          </p>
        </div>
        {children}
      </main>
    </div>
  );
}
