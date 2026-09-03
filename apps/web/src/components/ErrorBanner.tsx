interface ErrorBannerProps {
  message: string | null;
}

export function ErrorBanner({ message }: ErrorBannerProps) {
  if (message === null) {
    return null;
  }
  return (
    <p className="banner banner--error" role="alert">
      {message}
    </p>
  );
}
