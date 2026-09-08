import { useEffect, useRef, useState } from "react";
import { ErrorBanner } from "../components/ErrorBanner";

export function CameraCapture({
  onCapture,
  onClose,
}: {
  onCapture: (file: File) => Promise<void>;
  onClose: () => void;
}) {
  const video = useRef<HTMLVideoElement>(null);
  const [ready, setReady] = useState(false);
  const [capturing, setCapturing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let closed = false;
    let stream: MediaStream | null = null;
    async function open() {
      try {
        if (!navigator.mediaDevices?.getUserMedia) {
          throw new Error(
            "Camera capture is unavailable in this browser. You can choose a saved photo instead.",
          );
        }
        const acquired = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: "environment" },
            width: { ideal: 2400 },
          },
          audio: false,
        });
        if (closed) {
          acquired.getTracks().forEach((track) => track.stop());
          return;
        }
        stream = acquired;
        if (video.current) video.current.srcObject = acquired;
      } catch (cause) {
        if (closed) return;
        setError(
          cause instanceof DOMException
            ? "Could not open the camera. Check camera permission and availability, or choose a saved photo."
            : (cause as Error).message,
        );
      }
    }
    void open();
    return () => {
      closed = true;
      stream?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  async function capture() {
    const preview = video.current;
    if (!preview?.videoWidth || !preview.videoHeight) return;
    setCapturing(true);
    setError(null);
    try {
      const canvas = document.createElement("canvas");
      canvas.width = preview.videoWidth;
      canvas.height = preview.videoHeight;
      const context = canvas.getContext("2d");
      if (!context)
        throw new Error("Could not capture this page. Try another browser.");
      context.drawImage(preview, 0, 0);
      const blob = await new Promise<Blob | null>((resolve) =>
        canvas.toBlob(resolve, "image/jpeg", 0.9),
      );
      if (!blob) throw new Error("Could not capture this page. Try again.");
      await onCapture(
        new File([blob], `camera-${Date.now()}.jpg`, { type: "image/jpeg" }),
      );
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Could not capture this page. Try again.",
      );
    } finally {
      setCapturing(false);
    }
  }

  return (
    <section
      className="border-line bg-surface-sunk/60 flex flex-col gap-3 rounded-2xl border p-4"
      aria-label="Camera capture"
    >
      <div>
        <h3 className="text-base">Capture a page</h3>
        <p className="muted mt-1 text-sm">
          Keep the whole page in frame, with clear text and even light.
        </p>
      </div>
      <ErrorBanner message={error} />
      <video
        className="block max-h-96 w-full rounded-xl bg-[#14171b]"
        ref={video}
        autoPlay
        playsInline
        muted
        onLoadedData={() => setReady(true)}
        aria-label="Camera preview"
      />
      <div className="flex flex-wrap gap-2.5">
        <button
          className="button"
          type="button"
          disabled={!ready || capturing}
          onClick={() => void capture()}
        >
          {capturing ? "Capturing…" : "Capture page"}
        </button>
        <button
          className="button button--quiet"
          type="button"
          onClick={onClose}
        >
          Close camera
        </button>
      </div>
    </section>
  );
}
