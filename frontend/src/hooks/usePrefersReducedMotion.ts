import { useMediaQuery } from "./useMediaQuery";

/** Honour the user's reduced-motion preference. */
export function usePrefersReducedMotion(): boolean {
  return useMediaQuery("(prefers-reduced-motion: reduce)");
}
