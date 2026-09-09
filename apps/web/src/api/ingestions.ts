import type { components } from "../../../../contracts/api";
import { uploadRequest } from "./client";

export type IngestionUploadResult =
  components["schemas"]["IngestionUploadResult"];
export type UploadSource = "direct_file" | "camera";

export function uploadDocument(
  input: {
    files: File[];
    profileId: string;
    source: UploadSource;
    displayFilename: string;
    context: string;
  },
  onProgress: (percent: number) => void,
  signal: AbortSignal,
) {
  const body = new FormData();
  input.files.forEach((file) => body.append("uploads", file));
  body.append("provisional_profile_id", input.profileId);
  if (input.displayFilename.trim())
    body.append("display_filename", input.displayFilename.trim());
  if (input.context.trim()) body.append("user_context", input.context.trim());
  return uploadRequest<IngestionUploadResult>(
    input.source === "camera"
      ? "/ingestions/camera"
      : "/ingestions/direct-file",
    body,
    onProgress,
    signal,
  );
}
