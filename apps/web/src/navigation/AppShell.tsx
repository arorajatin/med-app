import {
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import { AccountMenu } from "../components/AccountMenu";
import { Wordmark } from "../components/BrandMark";
import { UploadTab } from "../upload/UploadTab";

const TABS = ["Feed", "Chat", "Upload", "Drive", "Profile"] as const;
type Tab = (typeof TABS)[number];

/** What each area is called once you are inside it, rather than on its tab. */
const SECTIONS: Record<Tab, { title: string; lead: string }> = {
  Feed: {
    title: "Family feed",
    lead: "What has arrived recently, across everyone you look after.",
  },
  Chat: {
    title: "Ask FamCare",
    lead: "Questions about a person’s records, answered from their own reports.",
  },
  Upload: {
    title: "Add a report",
    lead: "Keep a lab result or prescription safe the moment it reaches you.",
  },
  Drive: {
    title: "Family drive",
    lead: "Every report you have kept, filed under the person it belongs to.",
  },
  Profile: {
    title: "Your household",
    lead: "Your own health summary and the family profiles you manage.",
  },
};

/** The three areas whose milestones are still ahead of the upload release. */
const COMING: Record<"Feed" | "Chat" | "Drive", { headline: string; body: string }> = {
  Feed: {
    headline: "The family’s story, as it arrives",
    body: "Reports will land here the moment they finish uploading, newest first, with whatever still needs a look from you gently marked.",
  },
  Chat: {
    headline: "Ask about one person’s records",
    body: "Pick a family member and ask in plain words. Answers will cite the report they came from, and never mix one person’s history into another’s.",
  },
  Drive: {
    headline: "Every report, filed by person",
    body: "A calm shelf of everything you have kept, grouped by family member and by the kind of report it is.",
  },
};

export function AppShell({
  profile,
  email,
  onSignOut,
  onUnauthenticated,
}: {
  profile: ReactNode;
  email: string | null;
  onSignOut: () => void;
  onUnauthenticated: () => void;
}) {
  const [active, setActive] = useState<Tab>("Upload");
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);

  useEffect(() => {
    tabs.current[2]?.focus();
  }, []);

  function navigate(event: KeyboardEvent, index: number) {
    let next: number;
    if (event.key === "ArrowRight") next = (index + 1) % TABS.length;
    else if (event.key === "ArrowLeft")
      next = (index + TABS.length - 1) % TABS.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = TABS.length - 1;
    else return;
    event.preventDefault();
    const tab = TABS[next];
    if (!tab) return;
    setActive(tab);
    tabs.current[next]?.focus();
  }

  function openUpload() {
    setActive("Upload");
    tabs.current[2]?.focus();
  }

  const section = SECTIONS[active];

  return (
    <div className="bg-canvas min-h-dvh lg:grid lg:grid-cols-[16.5rem_1fr]">
      {/*
        One navigation element for both form factors: a bottom bar within thumb
        reach on a phone, and a resting sidebar once there is room for it.
      */}
      <nav
        aria-label="Main navigation"
        className="border-line bg-surface/95 fixed inset-x-0 bottom-0 z-20 border-t px-2 pt-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] backdrop-blur-md lg:sticky lg:inset-x-auto lg:top-0 lg:bottom-auto lg:flex lg:h-dvh lg:flex-col lg:border-t-0 lg:border-r lg:px-4 lg:py-7 lg:backdrop-blur-none"
      >
        <div className="hidden lg:mb-9 lg:block lg:px-2">
          <Wordmark />
        </div>
        <div
          role="tablist"
          aria-label="FamCare"
          className="grid grid-cols-5 gap-1 lg:flex lg:flex-col lg:gap-1"
        >
          {TABS.map((tab, index) => (
            <button
              key={tab}
              ref={(element) => {
                tabs.current[index] = element;
              }}
              id={`tab-${tab}`}
              type="button"
              role="tab"
              aria-selected={active === tab}
              aria-controls={`panel-${tab}`}
              tabIndex={active === tab ? 0 : -1}
              className="text-ink-soft aria-selected:bg-sage-soft aria-selected:text-sage flex cursor-pointer flex-col items-center gap-1 rounded-2xl px-1 py-1.5 text-[0.72rem] font-medium transition-colors hover:text-ink aria-selected:font-semibold lg:flex-row lg:gap-3 lg:rounded-full lg:px-3 lg:py-2 lg:text-[0.95rem]"
              onClick={() => setActive(tab)}
              onKeyDown={(event) => navigate(event, index)}
            >
              <span
                className={`flex h-8 w-8 flex-none items-center justify-center rounded-full transition-colors ${
                  tab === "Upload"
                    ? "bg-sage text-on-sage shadow-soft"
                    : "bg-transparent"
                }`}
              >
                <TabIcon tab={tab} />
              </span>
              <span>{tab}</span>
            </button>
          ))}
        </div>
      </nav>

      <div className="flex min-h-dvh flex-col">
        <header className="border-line bg-canvas/85 sticky top-0 z-10 flex items-center justify-between gap-4 border-b px-4 py-3 backdrop-blur-md lg:px-10 lg:py-5">
          <div className="lg:hidden">
            <Wordmark size="small" />
          </div>
          <div className="hidden min-w-0 lg:block">
            <h1 className="truncate text-2xl">{section.title}</h1>
            <p className="muted truncate text-sm">{section.lead}</p>
          </div>
          <AccountMenu email={email} onSignOut={onSignOut} />
        </header>

        <main className="mx-auto w-full max-w-3xl flex-1 px-4 pt-6 pb-28 sm:px-6 lg:max-w-4xl lg:px-10 lg:pt-8 lg:pb-14">
          {TABS.map((tab) => (
            <div
              key={tab}
              id={`panel-${tab}`}
              role="tabpanel"
              aria-labelledby={`tab-${tab}`}
              hidden={active !== tab}
              tabIndex={0}
            >
              {tab === "Upload" ? (
                <UploadTab
                  active={active === tab}
                  onUnauthenticated={onUnauthenticated}
                />
              ) : tab === "Profile" ? (
                active === tab ? (
                  profile
                ) : null
              ) : (
                <Placeholder tab={tab} onOpenUpload={openUpload} />
              )}
            </div>
          ))}
        </main>
      </div>
    </div>
  );
}

function Placeholder({
  tab,
  onOpenUpload,
}: {
  tab: "Feed" | "Chat" | "Drive";
  onOpenUpload: () => void;
}) {
  const copy = COMING[tab];
  return (
    <section className="panel items-center gap-5 py-12 text-center sm:py-16">
      <span className="bg-sage-soft text-sage ring-sage/20 flex h-20 w-20 items-center justify-center rounded-full ring-1">
        <span className="[&>svg]:h-9 [&>svg]:w-9">
          <TabIcon tab={tab} />
        </span>
      </span>
      <div className="max-w-md">
        <span className="bg-honey-soft text-ink inline-block rounded-full px-3 py-1 text-xs font-semibold tracking-wide">
          Coming soon
        </span>
        <h2 className="mt-3 text-2xl">{copy.headline}</h2>
        <p className="muted mt-2.5">{copy.body}</p>
      </div>
      <button className="button self-center" type="button" onClick={onOpenUpload}>
        Add a report now
      </button>
    </section>
  );
}

function TabIcon({ tab }: { tab: Tab }) {
  const paths: Record<Tab, ReactNode> = {
    Feed: (
      <>
        <rect x="4" y="3" width="16" height="18" rx="2.5" />
        <path d="M8 8h8M8 12h8M8 16h5" />
      </>
    ),
    Chat: <path d="M21 11a8 8 0 0 1-8 8H7l-4 3V11a9 9 0 0 1 18 0Z" />,
    Upload: (
      <path d="M12 16V3m-5 5 5-5 5 5M4 15v5a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-5" />
    ),
    Drive: (
      <path d="M3 7V5a2 2 0 0 1 2-2h5l3 4h6a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z" />
    ),
    Profile: (
      <>
        <circle cx="12" cy="7" r="4" />
        <path d="M4 21v-2a8 8 0 0 1 16 0v2" />
      </>
    ),
  };
  return (
    <svg
      className="h-[1.35rem] w-[1.35rem]"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[tab]}
    </svg>
  );
}
