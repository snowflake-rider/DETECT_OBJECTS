"use client";

import { ReactNode, useState } from "react";

interface QuickCheckProps {
  question: string;
  options: string[];
  correctAnswer: string;
  explanation: string;
  misconceptions: Record<string, string>;
  actionLabel?: string;
  promptContent?: ReactNode;
  onAttempt?: (correct: boolean) => void;
  onCorrect?: () => void;
}

export function QuickCheck({
  question,
  options,
  correctAnswer,
  explanation,
  misconceptions,
  actionLabel = "Check answer",
  promptContent,
  onAttempt,
  onCorrect,
}: QuickCheckProps) {
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<"correct" | "incorrect" | null>(null);
  const [attempts, setAttempts] = useState(0);

  function checkAnswer() {
    if (!answer) return;
    const correct = answer === correctAnswer;
    setAttempts((count) => count + 1);
    setResult(correct ? "correct" : "incorrect");
    onAttempt?.(correct);
    if (correct) onCorrect?.();
  }

  function select(option: string) {
    if (result === "correct") return;
    setAnswer(option);
    setResult(null);
  }

  return (
    <section className="quick-check" aria-label={question}>
      <h2 className="question-title">{question}</h2>
      {promptContent}
      <div className="answer-list" role="radiogroup" aria-label="Answer options">
        {options.map((option) => {
          const selected = answer === option;
          return (
            <button
              key={option}
              type="button"
              className={`answer-row ${selected ? "is-selected" : ""} ${
                selected && result ? `is-${result}` : ""
              }`}
              role="radio"
              aria-checked={selected}
              onClick={() => select(option)}
            >
              <span className="radio-mark"><span /></span>
              <span>{option}</span>
            </button>
          );
        })}
      </div>

      {result !== "correct" && (
        <button className="primary-action" type="button" disabled={!answer} onClick={checkAnswer}>
          {actionLabel}
        </button>
      )}

      {result && (
        <div className={`feedback feedback-${result}`} role="alert" aria-live="polite">
          <div className="feedback-title">
            {result === "correct" ? "You got it." : "Not quite — this is a useful trap."}
          </div>
          <p>{result === "correct" ? explanation : misconceptions[answer]}</p>
          {result === "incorrect" && (
            <button className="text-action" type="button" onClick={() => setResult(null)}>
              Try again
            </button>
          )}
        </div>
      )}

      {attempts > 0 && <p className="attempt-count">{attempts} {attempts === 1 ? "attempt" : "attempts"}</p>}
    </section>
  );
}
