export type RunResult =
  | { ok: true; output: string }
  | { ok: false; error: string };

type PythonValue = number | string | boolean;

const IDENTIFIER = /^[A-Za-z_][A-Za-z0-9_]*$/;

function splitAddition(expression: string): string[] {
  const parts: string[] = [];
  let current = "";
  let quote: "'" | '"' | null = null;

  for (const character of expression) {
    if ((character === "'" || character === '"') && quote === null) {
      quote = character;
      current += character;
      continue;
    }
    if (character === quote) {
      quote = null;
      current += character;
      continue;
    }
    if (character === "+" && quote === null) {
      parts.push(current.trim());
      current = "";
      continue;
    }
    current += character;
  }

  parts.push(current.trim());
  return parts;
}

function evaluateAtom(atom: string, environment: Map<string, PythonValue>): PythonValue {
  if (/^-?\d+(\.\d+)?$/.test(atom)) return Number(atom);
  if (atom === "True") return true;
  if (atom === "False") return false;
  if (
    atom.length >= 2 &&
    ((atom.startsWith('"') && atom.endsWith('"')) ||
      (atom.startsWith("'") && atom.endsWith("'")))
  ) {
    return atom.slice(1, -1);
  }
  if (IDENTIFIER.test(atom)) {
    if (!environment.has(atom)) throw new Error(`NameError: name '${atom}' is not defined`);
    return environment.get(atom)!;
  }
  throw new Error(`SyntaxError: this learning sandbox cannot parse “${atom}” yet`);
}

function evaluateExpression(expression: string, environment: Map<string, PythonValue>): PythonValue {
  const parts = splitAddition(expression);
  if (parts.length === 1) return evaluateAtom(parts[0], environment);

  const values = parts.map((part) => evaluateAtom(part, environment));
  let result = values[0];
  for (const value of values.slice(1)) {
    if (typeof result === "number" && typeof value === "number") result += value;
    else if (typeof result === "string" && typeof value === "string") result += value;
    else throw new Error("TypeError: '+' needs two numbers or two strings in this lesson");
  }
  return result;
}

export function runPythonBasics(code: string): RunResult {
  const environment = new Map<string, PythonValue>();
  const output: string[] = [];

  try {
    const lines = code.split("\n");
    lines.forEach((rawLine, index) => {
      const line = rawLine.trim();
      if (!line || line.startsWith("#")) return;

      const printMatch = line.match(/^print\((.*)\)$/);
      if (printMatch) {
        output.push(String(evaluateExpression(printMatch[1].trim(), environment)));
        return;
      }

      const assignmentMatch = line.match(/^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$/);
      if (assignmentMatch) {
        environment.set(
          assignmentMatch[1],
          evaluateExpression(assignmentMatch[2].trim(), environment),
        );
        return;
      }

      throw new Error(`SyntaxError on line ${index + 1}: expected an assignment or print(...)`);
    });

    return { ok: true, output: output.length > 0 ? output.join("\n") : "Program finished with no output." };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : String(error) };
  }
}
