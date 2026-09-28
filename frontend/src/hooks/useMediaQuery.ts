import { useEffect, useState } from "react";

/** Subscribe to a CSS media query. */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState<boolean>(() =>
    typeof window !== "undefined" ? window.matchMedia(query).matches : false
  );

  useEffect(() => {
    const mql = window.matchMedia(query);
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches);
    setMatches(mql.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, [query]);

  return matches;
}

/** True on screens narrower than the lg breakpoint (1024px). */
export function useIsMobile(): boolean {
  return useMediaQuery("(max-width: 1023px)");
}
