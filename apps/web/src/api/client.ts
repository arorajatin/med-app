import { readOptionalEnv } from "../env";

const DEFAULT_BASE_URL = "/api";

/** A failed API call, carrying the status and a message safe to show a person. */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH";
  body?: unknown;
}

type AccessTokenProvider = () => Promise<string | null>;

let provideAccessToken: AccessTokenProvider = async () => null;

/**
 * The token is fetched per request rather than passed in, so a token the
 * authentication client has since rotated can never be sent.
 */
export function setAccessTokenProvider(provider: AccessTokenProvider): void {
  provideAccessToken = provider;
}

export function apiBaseUrl(): string {
  return readOptionalEnv(import.meta.env.VITE_API_BASE_URL) ?? DEFAULT_BASE_URL;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body } = options;
  const token = await provideAccessToken();
  if (token === null) {
    throw new ApiError(401, "Your session has ended. Sign in again.");
  }
  const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "Could not reach the server. Check your connection and try again.");
  }

  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response));
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

/** FastAPI sends a string detail, or a list of field errors for a 422. */
async function readErrorMessage(response: Response): Promise<string> {
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    return fallbackMessage(response.status);
  }
  const detail = (payload as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string" && detail.trim() !== "") {
    return detail;
  }
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (item as { msg?: unknown }).msg)
      .filter((msg): msg is string => typeof msg === "string" && msg.trim() !== "")
      .map(stripPydanticPrefix);
    if (messages.length > 0) {
      return messages.join(" ");
    }
  }
  return fallbackMessage(response.status);
}

/** Multipart receipt uses XHR for actual upload progress; the browser sets the boundary. */
export async function uploadRequest<T>(
  path: string,
  body: FormData,
  onProgress: (percent: number) => void,
  signal: AbortSignal,
): Promise<T> {
  const token = await provideAccessToken();
  if (token === null) {
    throw new ApiError(401, "Your session has ended. Sign in again.");
  }
  if (signal.aborted) throw new DOMException("Upload cancelled", "AbortError");
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const abort = () => xhr.abort();
    xhr.open("POST", `${apiBaseUrl()}${path}`);
    xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.timeout = 120_000;
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round(event.loaded / event.total * 100));
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as T);
        } catch {
          reject(new ApiError(
            0,
            "Could not read the upload result. Check your connection before trying again.",
          ));
        }
      } else {
        void readErrorMessage(new Response(xhr.responseText, { status: xhr.status }))
          .then((message) => reject(new ApiError(xhr.status, message)));
      }
    };
    xhr.onerror = () => reject(new ApiError(
      0, "Could not reach the server. Check your connection and try again.",
    ));
    xhr.ontimeout = () => reject(new ApiError(
      0, "The upload timed out. Check your connection and try again.",
    ));
    xhr.onabort = () => reject(new DOMException("Upload cancelled", "AbortError"));
    xhr.onloadend = () => signal.removeEventListener("abort", abort);
    signal.addEventListener("abort", abort, { once: true });
    xhr.send(body);
  });
}

function stripPydanticPrefix(message: string): string {
  return message.replace(/^Value error,\s*/, "");
}

function fallbackMessage(status: number): string {
  if (status === 401) {
    return "Your session is no longer valid. Sign in again.";
  }
  if (status === 404) {
    return "That part of the app is not available for this deployment.";
  }
  return `The server rejected the request (status ${status}).`;
}
