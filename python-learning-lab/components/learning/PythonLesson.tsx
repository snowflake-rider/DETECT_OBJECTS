"use client";

import { useState } from "react";

import { useLessonProgress } from "@/hooks/useLessonProgress";

import { ConfidenceRating } from "./ConfidenceRating";
import { ProgressRail } from "./ProgressRail";
import { PythonPlayground } from "./PythonPlayground";
import { QuickCheck } from "./QuickCheck";

const starterCode = [
  ["score", "=", "7"],
  ["bonus", "=", "score"],
  ["score", "=", "10"],
  ["print", "(", "bonus", ")"],
];

export function PythonLesson() {
  const { state, percentage, complete, rate, reset, hydrated } = useLessonProgress();
  const [predictionAttempted, setPredictionAttempted] = useState(false);
  const [resetVersion, setResetVersion] = useState(0);

  const canRun = predictionAttempted || state.prediction;
  const explanationUnlocked = state.prediction;
  const lessonComplete = state.checkpoint && state.confidence !== null;

  function resetLesson() {
    reset();
    setPredictionAttempted(false);
    setResetVersion((version) => version + 1);
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">PY <span>/</span> LAB</div>
        <div className="course-title">Python Basics</div>
        <div className="header-progress" aria-label={`${percentage}% of lesson complete`}>
          <div className="progress-track"><span style={{ width: `${percentage}%` }} /></div>
          <span className="progress-copy">1 of 3</span>
          {hydrated && state.updatedAt && (
            <button className="reset-progress" type="button" onClick={resetLesson}>Reset progress</button>
          )}
        </div>
      </header>

      <div className="lesson-layout">
        <ProgressRail completed={lessonComplete} />

        <main className="lesson-main">
          <section className="lesson-intro">
            <h1>Names point to values</h1>
            <p>Predict the output, then test your mental model.</p>
          </section>

          <div className="rule" />

          <QuickCheck
            key={`prediction-${resetVersion}`}
            question="What does this program print?"
            options={["7", "10", "NameError"]}
            correctAnswer="7"
            explanation="bonus was bound to the value 7. Rebinding score later does not move bonus with it."
            misconceptions={{
              "10": "It is tempting to picture bonus as a live link to score. In Python, both names independently point to the value 7 at that moment.",
              NameError: "bonus was defined on line 2, so Python can resolve it when print runs.",
            }}
            promptContent={(
              <div className="source-card" aria-label="Python code being discussed">
                {starterCode.map((tokens, index) => (
                  <div className="source-line" key={index}>
                    <span className="source-number">{index + 1}</span>
                    <code>
                      {tokens.map((token, tokenIndex) => (
                        <span
                          key={`${token}-${tokenIndex}`}
                          className={/^\d+$/.test(token) ? "token-number" : token === "print" ? "token-function" : ""}
                        >{token}{tokenIndex < tokens.length - 1 ? " " : ""}</span>
                      ))}
                    </code>
                  </div>
                ))}
              </div>
            )}
            onAttempt={(correct) => {
              setPredictionAttempted(true);
              if (correct) complete("prediction");
            }}
          />

          <section className={`explanation ${explanationUnlocked ? "is-unlocked" : "is-locked"}`}>
            <div>
              <p className="section-label">Explain</p>
              <h2>Why this works</h2>
            </div>
            {explanationUnlocked ? (
              <>
                <p>
                  Assignment binds a name to a value. When <code>bonus = score</code> runs, both names point to
                  the integer <strong>7</strong>. The next assignment moves only <code>score</code> to 10.
                </p>
                <div className="binding-map" aria-label="Visual map of names and values">
                  <div><span className="binding-name">bonus</span><span className="binding-arrow">→</span><strong>7</strong></div>
                  <div><span className="binding-name">score</span><span className="binding-arrow">→</span><strong>10</strong></div>
                </div>
                <details>
                  <summary>Why say “binds” instead of “stores”?</summary>
                  <p>It keeps the mental model accurate: names refer to objects; they are not boxes that contain other names.</p>
                </details>
              </>
            ) : (
              <p className="locked-copy">Check your prediction to unlock the explanation.</p>
            )}
          </section>

          {explanationUnlocked && (
            <section className="checkpoint">
              <p className="section-label">Checkpoint</p>
              <pre><code>{`x = 3\ny = x\nx = x + 2\nprint(y)`}</code></pre>
              <QuickCheck
                question="Without running it: what prints now?"
                options={["3", "5", "TypeError"]}
                correctAnswer="3"
                explanation="y keeps its binding to 3. Rebinding x to 5 does not change y."
                misconceptions={{
                  "5": "That answer treats y as a live alias for x. The names became independent after the assignment.",
                  TypeError: "All operations use integers, so adding 2 is valid.",
                }}
                actionLabel="Check checkpoint"
                onCorrect={() => complete("checkpoint")}
              />
            </section>
          )}

          {state.checkpoint && (
            <ConfidenceRating value={state.confidence} onRate={rate} />
          )}

          {lessonComplete && (
            <section className="completion" role="status">
              <span className="completion-mark">✓</span>
              <div>
                <p className="section-label">Lesson complete</p>
                <h2>You can now predict simple name rebinding.</h2>
                <p>Your confidence choice and progress are saved locally for the next visit.</p>
              </div>
            </section>
          )}
        </main>

        <PythonPlayground key={`playground-${resetVersion}`} canRun={canRun} onRunComplete={() => complete("playground")} />
      </div>
    </div>
  );
}
