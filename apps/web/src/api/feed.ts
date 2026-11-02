import type { components } from "../../../../contracts/api";
import { request } from "./client";

export type FeedItem = components["schemas"]["FeedItemRead"];
export type FeedPage = components["schemas"]["FeedRead"];
export type FeedOrder = "upload_date" | "report_date";
export type ReportExtraction = components["schemas"]["ExtractionRead"];

/** The largest page `GET /feed` will serve in one request. */
export const FEED_MAX_LIMIT = 100;

export function listFeed(
  order: FeedOrder,
  cursor: string | null = null,
  limit?: number,
  profileId: string | null = null,
) {
  const query = new URLSearchParams({ order });
  if (cursor) query.set("cursor", cursor);
  if (limit !== undefined) query.set("limit", String(limit));
  if (profileId !== null) query.set("profile_id", profileId);
  return request<FeedPage>(`/feed?${query}`);
}

export function getReport(ingestionId: string) {
  return request<ReportExtraction>(
    `/ingestions/${encodeURIComponent(ingestionId)}/extraction`,
  );
}

export function assignReport(ingestionId: string, profileId: string) {
  return request<components["schemas"]["MedicalRecordRead"]>(
    `/ingestions/${encodeURIComponent(ingestionId)}/assignment/${encodeURIComponent(profileId)}`,
    { method: "POST" },
  );
}

export function retryReport(jobId: string) {
  return request<components["schemas"]["ExtractionJobRead"]>(
    `/extraction/jobs/${encodeURIComponent(jobId)}/retry`,
    { method: "POST" },
  );
}
