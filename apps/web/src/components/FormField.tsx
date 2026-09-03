import type { ReactNode } from "react";

interface FormFieldProps {
  id: string;
  label: string;
  hint?: string;
  error?: string | null;
  children: (describedBy: string | undefined) => ReactNode;
}

/** Wires a label, hint, and error message to one control for screen readers. */
export function FormField({ id, label, hint, error, children }: FormFieldProps) {
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;
  return (
    <div className="field">
      <label className="field__label" htmlFor={id}>
        {label}
      </label>
      {hint ? (
        <p className="field__hint" id={hintId}>
          {hint}
        </p>
      ) : null}
      {children(describedBy)}
      {error ? (
        <p className="field__error" id={errorId}>
          {error}
        </p>
      ) : null}
    </div>
  );
}
