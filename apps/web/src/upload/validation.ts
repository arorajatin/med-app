export const MAX_DOCUMENT_BYTES = 15_000_000;
export const MAX_IMAGE_BYTES = 10_000_000;
export const MAX_PARTS = 20;

export function fileKind(file: File): "pdf" | "image" | null {
  if (
    file.type === "application/pdf" ||
    (!file.type && /\.pdf$/i.test(file.name))
  )
    return "pdf";
  if (
    ["image/jpeg", "image/png"].includes(file.type) ||
    (!file.type && /\.(jpe?g|png)$/i.test(file.name))
  )
    return "image";
  return null;
}

export function validateFiles(files: File[], camera = false): string | null {
  if (!files.length) return "Choose a file or capture a page first.";
  if (files.length > MAX_PARTS)
    return "A report can contain up to 20 image pages.";
  if (files.some((file) => file.size === 0))
    return "This file is empty. Choose another file.";
  if (files.some((file) => fileKind(file) === null))
    return "Choose PDF, JPEG, or PNG files.";
  if (
    files.some((file) => fileKind(file) === "pdf") &&
    (camera || files.length > 1)
  ) {
    return "Upload one PDF or multiple images of the same report. PDFs cannot be combined.";
  }
  if (
    files.some(
      (file) => fileKind(file) === "image" && file.size > MAX_IMAGE_BYTES,
    )
  ) {
    return "Each image must be 10 MB or smaller.";
  }
  if (
    files.reduce((total, file) => total + file.size, 0) > MAX_DOCUMENT_BYTES
  ) {
    return "The whole report must be 15 MB or smaller.";
  }
  return null;
}

/** Decode selected images before receipt; the API separately validates the real content. */
export function validateImage(file: File): Promise<void> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(url);
      if (Math.max(image.naturalWidth, image.naturalHeight) > 10_000) {
        reject(
          new Error("Each image dimension must be 10,000 pixels or smaller."),
        );
      } else resolve();
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(
        new Error(
          "This image could not be opened. Choose another image or retake the photo.",
        ),
      );
    };
    image.src = url;
  });
}
