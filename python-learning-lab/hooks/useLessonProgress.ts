"use client";

import { useEffect, useMemo, useState } from "react";

export type Confidence = "low" | "medium" | "high";

interface LessonProgress {
  prediction: boolean;
  playground: boolean;
  checkpoint: boolean;
  confidence: Confidence | null;
  updatedAt: number | null;
}

const STORAGE_KEY = "py-lab:names-and-values";
const initialProgress: LessonProgress = {
  prediction: false,
  playground: false,
  checkpoint: false,
  confidence: null,
  updatedAt: null,
};

export function useLessonProgress() {
  const [state, setState] = useState<LessonProgress>(initialProgress);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY);
      if (saved) setState({ ...initialProgress, ...JSON.parse(saved) });
    } catch {
      // A blocked localStorage should not block the lesson.
    } finally {
      setHydrated(true);
    }
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      // Progress remains available in memory for this session.
    }
  }, [hydrated, state]);

  const percentage = useMemo(() => {
    let total = 15;
    if (state.prediction) total += 35;
    if (state.playground) total += 20;
    if (state.checkpoint) total += 20;
    if (state.confidence) total += 10;
    return total;
  }, [state]);

  function complete(field: "prediction" | "playground" | "checkpoint") {
    setState((current) => ({ ...current, [field]: true, updatedAt: Date.now() }));
  }

  function rate(confidence: Confidence) {
    setState((current) => ({ ...current, confidence, updatedAt: Date.now() }));
  }

  function reset() {
    setState(initialProgress);
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      // Nothing else to reset.
    }
  }

  return { state, percentage, complete, rate, reset, hydrated };
}
