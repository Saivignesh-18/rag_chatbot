import type { Variants, Transition } from "framer-motion";

// Reusable, restrained animation variants for a professional feel.

export const springSoft: Transition = { type: "spring", stiffness: 260, damping: 26 };

export const fadeInUp: Variants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.28, ease: "easeOut" } },
  exit: { opacity: 0, y: -8, transition: { duration: 0.18 } },
};

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: 0.25 } },
  exit: { opacity: 0, transition: { duration: 0.15 } },
};

export const listStagger: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.05 } },
};

export const drawerLeft: Variants = {
  hidden: { x: "-100%" },
  show: { x: 0, transition: springSoft },
  exit: { x: "-100%", transition: { duration: 0.2 } },
};

export const drawerRight: Variants = {
  hidden: { x: "100%" },
  show: { x: 0, transition: springSoft },
  exit: { x: "100%", transition: { duration: 0.2 } },
};

export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.96 },
  show: { opacity: 1, scale: 1, transition: { duration: 0.2 } },
  exit: { opacity: 0, scale: 0.96, transition: { duration: 0.15 } },
};
