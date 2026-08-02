"use client";

import type { Confidence } from "@/hooks/useLessonProgress";

interface ConfidenceRatingProps {
  value: Confidence | null;
  onRate: (confidence: Confidence) => void;
}

const levels: { value: Confidence; label: string; description: string }[] = [
  { value: "low", label: "Guessed", description: "Review tomorrow" },
  { value: "medium", label: "Mostly sure", description: "Review in 3 days" },
  { value: "high", label: "Confident", description: "Review in 7 days" },
];

export function ConfidenceRating({ value, onRate }: ConfidenceRatingProps) {
  return (
    <section className="confidence" aria-labelledby="confidence-heading">
      <div>
        <p className="section-label">Reflection</p>
        <h3 id="confidence-heading">How confident does this feel now?</h3>
      </div>
      <div className="confidence-options">
        {levels.map((level) => (
          <button
            type="button"
            key={level.value}
            className={value === level.value ? "is-selected" : ""}
            onClick={() => onRate(level.value)}
          >
            <strong>{level.label}</strong>
            <span>{level.description}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
