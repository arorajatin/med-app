import type { OnboardingStep } from "../api/types";
import { ONBOARDING_STEPS, STEP_LABELS } from "../onboarding/steps";

interface StepIndicatorProps {
  completedSteps: OnboardingStep[];
  activeStep: OnboardingStep | null;
  onSelectStep: (step: OnboardingStep) => void;
}

export function StepIndicator({ completedSteps, activeStep, onSelectStep }: StepIndicatorProps) {
  const done = completedSteps.length;
  return (
    <nav aria-label="Onboarding steps" className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-4">
        <p className="eyebrow">
          Step {Math.min(done + 1, ONBOARDING_STEPS.length)} of {ONBOARDING_STEPS.length}
        </p>
        <div className="bg-surface-sunk h-1.5 w-32 overflow-hidden rounded-full sm:w-44">
          <div
            className="bg-sage h-full rounded-full transition-[width] duration-500"
            style={{ width: `${(done / ONBOARDING_STEPS.length) * 100}%` }}
          />
        </div>
      </div>
      <ol className="grid gap-1.5 sm:grid-cols-2">
        {ONBOARDING_STEPS.map((step, index) => {
          const complete = completedSteps.includes(step);
          const current = step === activeStep;
          // The circle is decorative: the label beside it carries the meaning,
          // and it stays out of the edit button's accessible name.
          const circle = (
            <span
              aria-hidden="true"
              className={`flex h-7 w-7 flex-none items-center justify-center rounded-full text-sm font-semibold ${
                complete
                  ? "bg-sage text-on-sage"
                  : current
                    ? "bg-clay text-white"
                    : "bg-surface-sunk text-ink-soft"
              }`}
            >
              {complete ? "✓" : index + 1}
            </span>
          );
          return (
            <li
              key={step}
              aria-current={current ? "step" : undefined}
              className={`flex items-center gap-2.5 rounded-2xl border px-3 py-2.5 ${
                current
                  ? "border-clay/40 bg-clay-soft"
                  : complete
                    ? "border-line bg-surface"
                    : "border-line/70 border-dashed"
              }`}
            >
              {complete && !current ? (
                <button
                  type="button"
                  className="hover:text-sage flex min-w-0 cursor-pointer items-center gap-2.5 text-left text-sm font-semibold underline decoration-transparent underline-offset-4 transition-colors hover:decoration-current"
                  onClick={() => onSelectStep(step)}
                >
                  {circle}
                  <span className="truncate">{STEP_LABELS[step]}</span>
                </button>
              ) : (
                <span className="flex min-w-0 items-center gap-2.5 text-sm font-semibold">
                  {circle}
                  <span className="truncate">{STEP_LABELS[step]}</span>
                </span>
              )}
              <span className="muted ml-auto pl-2 text-xs whitespace-nowrap">
                {complete ? "Done" : current ? "In progress" : "Not started"}
              </span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
