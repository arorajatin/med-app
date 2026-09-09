interface ErrorBannerProps {
  message: string | null;
}

export function ErrorBanner({ message }: ErrorBannerProps) {
  if (message === null) {
    return null;
  }
  return (
    <p className="banner banner--error flex items-start gap-2.5" role="alert">
      <span aria-hidden="true" className="mt-px font-bold">
        !
      </span>
      <span>{message}</span>
    </p>
  );
}
