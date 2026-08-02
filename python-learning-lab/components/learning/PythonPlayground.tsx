"use client";

import { useEffect, useMemo, useState } from "react";

import { runPythonBasics } from "@/lib/pythonBasicsInterpreter";

const DEFAULT_CODE = `score = 7
bonus = score
score = 10
print(bonus)`;

interface PythonPlaygroundProps {
  canRun: boolean;
  onRunComplete: () => void;
}

function PlayIcon() {
  return <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2.8v10.4L13 8 4 2.8Z" fill="currentColor" /></svg>;
}

function ResetIcon() {
  return <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M13.4 5.1A6 6 0 1 0 14 9h-1.6a4.4 4.4 0 1 1-.3-2.2L9.8 7H15V1.8l-1.6 1.6v1.7Z" fill="currentColor" /></svg>;
}

export function PythonPlayground({ canRun, onRunComplete }: PythonPlaygroundProps) {
  const [code, setCode] = useState(DEFAULT_CODE);
  const [consoleText, setConsoleText] = useState("");
  const [consoleState, setConsoleState] = useState<"idle" | "success" | "error" | "nudge">("idle");

  useEffect(() => {
    const savedCode = new URLSearchParams(window.location.search).get("code");
    if (savedCode) setCode(savedCode);
  }, []);

  const lineNumbers = useMemo(() => code.split("\n").map((_, index) => index + 1), [code]);

  function updateCode(nextCode: string) {
    setCode(nextCode);
    setConsoleText("");
    setConsoleState("idle");
    const url = new URL(window.location.href);
    if (nextCode === DEFAULT_CODE) url.searchParams.delete("code");
    else url.searchParams.set("code", nextCode);
    window.history.replaceState({}, "", url);
  }

  function run() {
    if (!canRun) {
      setConsoleState("nudge");
      setConsoleText("Make a prediction first. Then run the code to test it.");
      return;
    }
    const result = runPythonBasics(code);
    if (result.ok) {
      setConsoleState("success");
      setConsoleText(result.output);
      onRunComplete();
    } else {
      setConsoleState("error");
      setConsoleText(result.error);
    }
  }

  function reset() {
    updateCode(DEFAULT_CODE);
  }

  return (
    <aside className="playground-panel" aria-label="Python playground">
      <div className="playground-header">
        <p className="panel-title">Python playground</p>
        <div className="playground-actions">
          <button className="secondary-action" type="button" onClick={reset}>
            <ResetIcon /> Reset
          </button>
          <button className="run-action" type="button" onClick={run}>
            <PlayIcon /> Run
          </button>
        </div>
      </div>

      <div className="code-editor-frame">
        <div className="line-numbers" aria-hidden="true">
          {lineNumbers.map((line) => <span key={line}>{line}</span>)}
        </div>
        <textarea
          aria-label="Editable Python code"
          value={code}
          spellCheck={false}
          onChange={(event) => updateCode(event.target.value)}
          onKeyDown={(event) => {
            if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
              event.preventDefault();
              run();
            }
          }}
        />
      </div>

      <div className="console-heading">
        <span>Console</span>
        <span className="shortcut">⌘ Enter to run</span>
      </div>
      <div className={`console-output console-${consoleState}`} aria-live="polite">
        {consoleText || <span className="console-placeholder">Output will appear here.</span>}
      </div>
      <p className="sandbox-note">Safe lesson sandbox: assignments, values, +, and print().</p>
    </aside>
  );
}
