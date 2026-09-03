import type { OnboardingStep } from "../api/types";
import { ONBOARDING_STEPS, STEP_LABELS } from "../onboarding/steps";

interface StepIndicatorProps {
  completedSteps: OnboardingStep[];
  activeStep: OnboardingStep | null;
  onSelectStep: (step: OnboardingStep) => void;
}

export function StepIndicator({ completedSteps, activeStep, onSelectStep }: StepIndicatorProps) {
  return (
    <nav aria-label="Onboarding steps">
      <ol className="steps">
        {ONBOARDING_STEPS.map((step, index) => {
          const done = completedSteps.includes(step);
          const current = step === activeStep;
          return (
            <li
              key={step}
              className={`steps__item${current ? " steps__item--current" : ""}${
                done ? " steps__item--done" : ""
              }`}
              aria-current={current ? "step" : undefined}
            >
              <span className="steps__number" aria-hidden="true">
                {done ? "✓" : index + 1}
              </span>
              {done && !current ? (
                <button type="button" className="steps__link" onClick={() => onSelectStep(step)}>
                  {STEP_LABELS[step]}
                </button>
              ) : (
                <span className="steps__label">{STEP_LABELS[step]}</span>
              )}
              <span className="steps__state">
                {done ? "Done" : current ? "In progress" : "Not started"}
              </span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
