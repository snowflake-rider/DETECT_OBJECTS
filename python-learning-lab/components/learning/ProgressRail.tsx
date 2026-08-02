interface ProgressRailProps {
  completed: boolean;
}

const lessons = [
  { number: 1, title: "Names & values", state: "current" },
  { number: 2, title: "Types", state: "pending" },
  { number: 3, title: "Conditionals", state: "pending" },
] as const;

export function ProgressRail({ completed }: ProgressRailProps) {
  return (
    <aside className="progress-rail" aria-label="Course progress">
      <p className="rail-heading">Foundations</p>
      <ol className="lesson-list">
        {lessons.map((lesson) => (
          <li key={lesson.number}>
            <div
              className={`lesson-row ${lesson.state === "current" ? "is-current" : "is-pending"}`}
              aria-current={lesson.state === "current" ? "step" : undefined}
            >
              <span className={`lesson-number ${completed && lesson.number === 1 ? "is-complete" : ""}`}>
                {completed && lesson.number === 1 ? "✓" : lesson.number}
              </span>
              <span>{lesson.title}</span>
            </div>
          </li>
        ))}
      </ol>
      <div className="rail-note">
        <span className="rail-note-dot" />
        Test drive · lesson 1 only
      </div>
    </aside>
  );
}
