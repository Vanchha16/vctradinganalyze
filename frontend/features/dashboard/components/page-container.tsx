"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";

/**
 * Shared by every page's main content area - a single subtle fade-in
 * here gives every page the same tasteful entrance transition (docs/05
 * §19: minimal animation) without adding it per-page.
 */
export function PageContainer({ children }: { children: ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
      className="mx-auto w-full max-w-screen-2xl"
    >
      {children}
    </motion.div>
  );
}
