import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const url: string = (import.meta.env.VITE_SUPABASE_URL ?? "").trim();
const anonKey: string = (import.meta.env.VITE_SUPABASE_ANON_KEY ?? "").trim();

/**
 * Both values are meant to ship in the bundle. The anon key is publishable and
 * grants nothing on its own; row-level security and the API decide what a signed
 * in person may read.
 */
export const isAuthConfigured: boolean = url !== "" && anonKey !== "";

const client: SupabaseClient | null = isAuthConfigured
  ? createClient(url, anonKey, {
      auth: {
        // PKCE returns an authorization code to exchange, so no access token is
        // ever placed in the URL where history and referrers could keep it.
        flowType: "pkce",
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    })
  : null;

export function requireSupabase(): SupabaseClient {
  if (client === null) {
    throw new Error(
      "Sign-in is not configured for this build. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.",
    );
  }
  return client;
}
