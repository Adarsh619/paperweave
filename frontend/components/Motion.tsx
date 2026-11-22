"use client";

import { MotionConfig, motion } from "motion/react";
import type { ReactNode } from "react";

import SpotlightCard from "@/components/reactbits/SpotlightCard";
import Threads from "@/components/reactbits/Threads";
import { useColorScheme } from "@/lib/useColorScheme";

/** Honour the OS "reduce motion" setting for every motion-based animation (BlurText, CountUp, fades). */
export function MotionProvider({ children }: { children: ReactNode }) {
  return <MotionConfig reducedMotion="user">{children}</MotionConfig>;
}

/** Fade a section up as it scrolls into view, once. */
export function Reveal({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.5, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}

/** The hero's woven-threads background, in ink with a vermilion accent thread. */
export function HeroThreads() {
  const dark = useColorScheme() === "dark";
  return (
    <Threads
      color={dark ? "#8fb0e0" : "#2b4c7e"}
      accentColor={dark ? "#f0876a" : "#b4432c"}
      opacity={dark ? 0.45 : 0.35}
      amplitude={1.2}
      lineCount={60}
      speed={0.35}
    />
  );
}

/** React Bits spotlight card, recoloured with the site's paper/ink tokens. */
export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  const theme = useColorScheme();
  return (
    <SpotlightCard
      theme={theme}
      spotlightColor={theme === "dark" ? "rgba(240, 135, 106, 0.22)" : "rgba(180, 67, 44, 0.14)"}
      className={`!rounded-xl !p-5 border border-border ${className}`}
      style={{ "--spotlight-card-surface": "var(--surface)", "--spotlight-card-border": "var(--border)" } as React.CSSProperties}
    >
      {children}
    </SpotlightCard>
  );
}
