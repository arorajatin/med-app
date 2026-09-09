import type { ReactNode } from "react";
import { Wordmark } from "../components/BrandMark";
import { ThemeToggle } from "../components/ThemeToggle";

const PROMISES = [
  {
    title: "Private from the first upload",
    detail: "Reports are stored for your account alone, never shared or sold.",
    icon: (
      <>
        <rect x="4" y="10" width="16" height="11" rx="2.5" />
        <path d="M8 10V7a4 4 0 0 1 8 0v3" />
      </>
    ),
  },
  {
    title: "One home for everyone",
    detail: "Parents, partners, children — each with their own place in the house.",
    icon: (
      <>
        <circle cx="8.5" cy="9" r="3" />
        <circle cx="16.5" cy="10.5" r="2.4" />
        <path d="M3 20a5.5 5.5 0 0 1 11 0M15 20a4.5 4.5 0 0 1 6-4" />
      </>
    ),
  },
  {
    title: "Reports you can actually read",
    detail: "Lab results and prescriptions, turned into plain language you can revisit.",
    icon: (
      <>
        <path d="M6 3h8l4 4v14a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z" />
        <path d="M13.5 3v4.5H18M8.5 13h7M8.5 17h4.5" />
      </>
    ),
  },
];

/**
 * The way into FamCare: a warm welcome panel beside whatever the account needs
 * to do next, whether that is signing in or waiting for a session to restore.
 */
export function EntryLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[1.05fr_1fr]">
      <aside className="bg-canvas-deep relative isolate overflow-hidden px-5 pt-10 pb-12 lg:flex lg:flex-col lg:justify-between lg:px-14 lg:py-14">
        <Glow />
        <div className="flex items-start justify-between gap-4">
          <Wordmark tagline />
          <ThemeToggle />
        </div>
        <div className="mt-9 max-w-lg lg:mt-0">
          <h1 className="text-[2.1rem] leading-[1.12] sm:text-5xl">
            Every report your family collects,
            <span className="text-sage"> under one roof.</span>
          </h1>
          <p className="text-ink-soft mt-4 text-base sm:text-lg">
            Lab results, prescriptions, discharge summaries. Keep them for the people you
            look after, and stop hunting through folders and photo rolls.
          </p>
        </div>
        <ul className="mt-9 flex flex-col gap-4 lg:mt-0">
          {PROMISES.map((promise) => (
            <li key={promise.title} className="flex items-start gap-3.5">
              <span className="bg-surface ring-line text-sage flex h-10 w-10 flex-none items-center justify-center rounded-full ring-1">
                <svg
                  className="h-5 w-5"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  {promise.icon}
                </svg>
              </span>
              <span>
                <span className="block font-semibold">{promise.title}</span>
                <span className="text-ink-soft block text-sm">{promise.detail}</span>
              </span>
            </li>
          ))}
        </ul>
      </aside>
      <main className="flex items-center justify-center px-4 py-10 sm:px-8 lg:px-12">
        <div className="w-full max-w-md">{children}</div>
      </main>
    </div>
  );
}

/** Soft light behind the welcome panel, in place of a photograph. */
function Glow() {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10">
      <div className="bg-sage/20 absolute -top-24 -left-24 h-80 w-80 rounded-full blur-3xl" />
      <div className="bg-clay/15 absolute right-[-6rem] bottom-[-8rem] h-96 w-96 rounded-full blur-3xl" />
      <div className="bg-honey/10 absolute top-1/3 right-1/4 h-56 w-56 rounded-full blur-3xl" />
    </div>
  );
}
