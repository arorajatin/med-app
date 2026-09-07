import { request } from "./client";
import type { ProfileRead } from "./types";

export function listProfiles(): Promise<ProfileRead[]> {
  return request<ProfileRead[]>("/profiles");
}

export function createProfile(input: {
  displayName: string;
  relationship: string;
  sex: string | null;
}): Promise<ProfileRead> {
  return request<ProfileRead>("/profiles", {
    method: "POST",
    body: {
      display_name: input.displayName,
      relationship: input.relationship,
      sex: input.sex,
    },
  });
}
