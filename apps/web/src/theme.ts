import { useCallback, useEffect, useState } from "react";

export type Theme = "light" | "dark";

/** Shared with the inline script in index.html, which applies the theme before paint. */
export const THEME_STORAGE_KEY = "famcare-theme";

function systemTheme(): Theme {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/**
 * The theme already on the document. The inline boot script sets it, so this
 * agrees with what is on screen rather than re-deciding it.
 */
function currentTheme(): Theme {
  return document.documentElement.dataset["theme"] === "dark" ? "dark" : "light";
}

/**
 * The chosen theme and a way to change it. A choice is remembered for this
 * browser; without one the account follows the operating system.
 */
export function useTheme(): { theme: Theme; toggleTheme: () => void } {
  const [theme, setTheme] = useState<Theme>(currentTheme);

  // Until someone chooses, the system decides, including while the tab is open.
  useEffect(() => {
    const media = window.matchMedia?.("(prefers-color-scheme: dark)");
    if (!media) return;
    const follow = () => {
      if (localStorage.getItem(THEME_STORAGE_KEY) === null) {
        apply(systemTheme());
        setTheme(systemTheme());
      }
    };
    media.addEventListener("change", follow);
    return () => media.removeEventListener("change", follow);
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme((current) => {
      const next: Theme = current === "dark" ? "light" : "dark";
      apply(next);
      try {
        localStorage.setItem(THEME_STORAGE_KEY, next);
      } catch {
        // A blocked store only costs the preference on the next visit.
      }
      return next;
    });
  }, []);

  return { theme, toggleTheme };
}

function apply(theme: Theme) {
  document.documentElement.dataset["theme"] = theme;
}
