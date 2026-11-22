"use client";

import { useMemo, useSyncExternalStore } from "react";

// This visitor's recent questions, kept in their own browser only.
const KEY = "pw:recent";
const EVENT = "pw:recent";
const MAX = 8;

function read(): string {
  try {
    return localStorage.getItem(KEY) ?? "[]";
  } catch {
    return "[]"; // private mode or blocked storage: no history
  }
}

function parse(raw: string): string[] {
  try {
    const list = JSON.parse(raw);
    return Array.isArray(list) ? list.filter((q): q is string => typeof q === "string") : [];
  } catch {
    return [];
  }
}

export function addRecent(question: string) {
  const q = question.trim();
  const next = [q, ...parse(read()).filter((x) => x.toLowerCase() !== q.toLowerCase())].slice(0, MAX);
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    return;
  }
  window.dispatchEvent(new Event(EVENT));
}

function subscribe(onChange: () => void) {
  window.addEventListener(EVENT, onChange);
  window.addEventListener("storage", onChange); // other tabs
  return () => {
    window.removeEventListener(EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

export function useRecent(): string[] {
  const raw = useSyncExternalStore(subscribe, read, () => "[]");
  return useMemo(() => parse(raw), [raw]);
}
