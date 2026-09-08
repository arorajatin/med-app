import { vi } from "vitest";
import type { IngestionUploadResult } from "../api/ingestions";

export const UPLOAD_RESULT: IngestionUploadResult = {
  ingestion: {
    id: "ingestion_1",
    provisional_profile_id: "profile_1",
    resolved_profile_id: null,
    source_channel: "direct_file",
    user_context: null,
    display_filename: "report.pdf",
    upload_state: "complete",
    assignment_state: "provisional",
    extraction_state: "queued",
    review_state: "not_required",
    completed_at: "2026-09-07T10:00:00Z",
    resolved_at: null,
    created_at: "2026-09-07T10:00:00Z",
    updated_at: "2026-09-07T10:00:00Z",
  },
  parts: [
    {
      id: "part_1",
      ingestion_id: "ingestion_1",
      ordinal: 0,
      original_filename: "report.pdf",
      detected_mime_type: "application/pdf",
      size_bytes: 100,
      received_at: "2026-09-07T10:00:00Z",
    },
  ],
  record: null,
  extraction_job: {
    id: "job_1",
    ingestion_id: "ingestion_1",
    status: "queued",
    current_phase: null,
    failure_code: null,
    created_at: "2026-09-07T10:00:00Z",
    started_at: null,
    finished_at: null,
  },
};

/** Exercise the multipart client while controlling transport progress and receipt separately. */
export function mockUploadTransport() {
  const instances: FakeXHR[] = [];
  class FakeXHR {
    status = 0;
    responseText = "";
    timeout = 0;
    upload = {
      onprogress: null as
        | ((event: {
            lengthComputable: boolean;
            loaded: number;
            total: number;
          }) => void)
        | null,
    };
    onload: (() => void) | null = null;
    onloadend: (() => void) | null = null;
    onerror: (() => void) | null = null;
    ontimeout: (() => void) | null = null;
    onabort: (() => void) | null = null;
    body: FormData | null = null;
    open = vi.fn();
    setRequestHeader = vi.fn();
    abort = vi.fn(() => {
      this.onabort?.();
      this.onloadend?.();
    });

    constructor() {
      instances.push(this);
    }
    send(body: FormData) {
      this.body = body;
    }
    progress(percent: number) {
      this.upload.onprogress?.({
        lengthComputable: true,
        loaded: percent,
        total: 100,
      });
    }
    respond(body: unknown = UPLOAD_RESULT, status = 201) {
      this.status = status;
      this.responseText = JSON.stringify(body);
      this.onload?.();
      this.onloadend?.();
    }
  }
  vi.stubGlobal("XMLHttpRequest", FakeXHR);
  return instances;
}
