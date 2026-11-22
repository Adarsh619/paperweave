"use client";

import { useEffect, useRef, useState } from "react";

/** Reveal text at a steady pace. Groq streams a whole answer in about a second, which reads as a jump.
 * Long backlogs speed up so a finished answer never takes more than a few seconds to appear. */
export function useSmoothText(target: string): string {
  const [shown, setShown] = useState("");
  const shownRef = useRef("");

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      shownRef.current = target;
      const id = requestAnimationFrame(() => setShown(target));
      return () => cancelAnimationFrame(id);
    }
    let raf = 0;
    const tick = () => {
      let base = shownRef.current;
      // The verified answer can differ from the raw stream (repaired citations): keep the shared prefix.
      if (!target.startsWith(base)) {
        let i = 0;
        while (i < base.length && base[i] === target[i]) i++;
        base = target.slice(0, i);
      }
      const rest = target.length - base.length;
      const next = rest <= 0 ? target : target.slice(0, base.length + Math.max(3, Math.ceil(rest / 90)));
      shownRef.current = next;
      setShown(next);
      if (next !== target) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target]);

  return shown;
}
