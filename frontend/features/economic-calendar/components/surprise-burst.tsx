"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";

/**
 * A one-shot burst that fires across the whole viewport when the analysis
 * dialog opens (ADR-153).
 *
 * Rendered through a portal to `document.body` on purpose. `DialogContent`
 * carries both a `transform` and `overflow-y-auto`, and a transformed
 * ancestor becomes the containing block for `position: fixed` descendants -
 * so a burst rendered inside the panel would be positioned against the
 * panel and then clipped by its scroll box, instead of covering the screen.
 *
 * `pointer-events-none` throughout: this is decoration and must never
 * intercept a click meant for the dialog beneath it.
 */

const PARTICLE_COUNT = 28;

/** Theme tokens, not literals, so the burst follows light/dark and any
 * future palette change (globals.css). */
const COLORS = [
  "var(--primary)",
  "var(--success)",
  "var(--warning)",
  "var(--chart-3)",
  "var(--chart-2)",
];

interface Particle {
  id: number;
  dx: number;
  dy: number;
  size: number;
  color: string;
  rotate: number;
  delay: number;
  radius: string;
}

/**
 * Evenly spaced angles with jitter, rather than fully random ones: pure
 * `Math.random()` on 28 particles reliably leaves visible gaps and clumps.
 *
 * Travel distance is a fraction of the viewport's own half-diagonal, not a
 * fixed pixel count: a 400px throw covers a laptop screen but barely
 * leaves the panel on a wide monitor, and the effect has to read as
 * "across the screen" on both.
 */
function buildParticles(viewportW: number, viewportH: number): Particle[] {
  const reach = Math.hypot(viewportW, viewportH) / 2;
  return Array.from({ length: PARTICLE_COUNT }, (_, i) => {
    const spread = (Math.PI * 2) / PARTICLE_COUNT;
    const angle = i * spread + (Math.random() - 0.5) * spread * 0.8;
    const distance = reach * (0.55 + Math.random() * 0.45);
    return {
      id: i,
      dx: Math.cos(angle) * distance,
      dy: Math.sin(angle) * distance,
      size: 6 + Math.random() * 8,
      color: COLORS[i % COLORS.length],
      rotate: (Math.random() - 0.5) * 540,
      delay: Math.random() * 0.08,
      // A mix of dots and rectangles reads as confetti; all-circles reads
      // as a loading spinner exploding.
      radius: i % 3 === 0 ? "9999px" : "2px",
    };
  });
}

export function SurpriseBurst({ fireKey }: { fireKey: number }) {
  const reduced = useReducedMotion();
  const [mounted, setMounted] = useState(false);

  // `document`/`window` do not exist during SSR; the portal target and the
  // viewport size only become available after mount.
  useEffect(() => setMounted(true), []);

  // Regenerated per firing (the component is remounted by key) so two
  // opens never look identical.
  const particles = useMemo(
    () => (mounted ? buildParticles(window.innerWidth, window.innerHeight) : []),
    [mounted],
  );

  if (!mounted || reduced) return null;

  return createPortal(
    <div
      key={fireKey}
      aria-hidden
      className="pointer-events-none fixed inset-0 z-[60] overflow-hidden"
    >
      {/* Shockwave: one expanding ring that reaches past the panel edges,
          which is what makes the effect read as "around the screen" rather
          than "inside the dialog". */}
      <motion.div
        className="absolute left-1/2 top-1/2 rounded-full border-2"
        style={{ borderColor: "var(--primary)", width: 220, height: 220, x: "-50%", y: "-50%" }}
        initial={{ scale: 0.2, opacity: 0.55 }}
        animate={{ scale: Math.hypot(window.innerWidth, window.innerHeight) / 220, opacity: 0 }}
        transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
      />
      <motion.div
        className="absolute left-1/2 top-1/2 rounded-full"
        style={{
          width: 320,
          height: 320,
          x: "-50%",
          y: "-50%",
          background:
            "radial-gradient(circle, color-mix(in oklab, var(--primary) 45%, transparent) 0%, transparent 70%)",
        }}
        initial={{ scale: 0.3, opacity: 0.7 }}
        animate={{ scale: 3.2, opacity: 0 }}
        transition={{ duration: 0.7, ease: "easeOut" }}
      />

      {particles.map((p) => (
        <motion.span
          key={p.id}
          className="absolute left-1/2 top-1/2 block"
          style={{
            width: p.size,
            height: p.size,
            backgroundColor: p.color,
            borderRadius: p.radius,
          }}
          initial={{ x: "-50%", y: "-50%", scale: 0, opacity: 1, rotate: 0 }}
          animate={{
            x: p.dx,
            y: [0, p.dy * 0.82, p.dy + 90], // slight gravity on the tail
            scale: [0, 1, 0.9, 0],
            opacity: [1, 1, 0.9, 0],
            rotate: p.rotate,
          }}
          transition={{
            duration: 1.05,
            delay: p.delay,
            ease: [0.2, 0.7, 0.3, 1],
            times: [0, 0.25, 0.6, 1],
          }}
        />
      ))}
    </div>,
    document.body,
  );
}
