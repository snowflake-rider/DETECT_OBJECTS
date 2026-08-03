"""Generate a structured visual story with the locally authenticated Codex CLI."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
from typing import Any, Protocol


class StoryGenerationError(RuntimeError):
    """Raised when a recorded session cannot become a valid story."""


@dataclass(frozen=True)
class StoryResult:
    """The short generated story and its selected session image."""

    title: str
    story: str
    representative_image: Path


class StoryGenerator(Protocol):
    """Story generation boundary used by the Desktop worker."""

    def generate(self, session_dir: Path) -> StoryResult: ...


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


class CodexStoryGenerator:
    """Send session events and snapshots to ``codex exec``."""

    def __init__(
        self,
        *,
        executable: str = "codex",
        timeout_seconds: float = 120.0,
        runner: CommandRunner = subprocess.run,
    ) -> None:
        self._executable = executable
        self._timeout_seconds = timeout_seconds
        self._runner = runner

    def generate(self, session_dir: Path) -> StoryResult:
        """Generate and persist one story for a completed or active session."""
        events_path = session_dir / "events.json"
        if not events_path.is_file():
            raise StoryGenerationError(f"Session events were not found: {events_path}")

        snapshot_paths = tuple(sorted((session_dir / "snapshots").glob("*.png")))
        if not snapshot_paths:
            raise StoryGenerationError("No matching snapshots are available yet.")

        events_text = events_path.read_text(encoding="utf-8")
        command = self._build_command(session_dir, snapshot_paths)
        try:
            completed = self._runner(
                command,
                input=self._build_prompt(events_text),
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
                check=False,
            )
        except FileNotFoundError as error:
            raise StoryGenerationError(
                "Codex CLI was not found. Install it and sign in before generating a story."
            ) from error
        except subprocess.TimeoutExpired as error:
            raise StoryGenerationError("Codex story generation timed out.") from error

        if completed.returncode != 0:
            detail = (
                completed.stderr.strip() or "Codex exited without an error message."
            )
            raise StoryGenerationError(f"Codex story generation failed: {detail}")

        document = _parse_story_document(completed.stdout)
        representative_image = (
            session_dir / document["representative_image"]
        ).resolve()
        snapshot_directory = (session_dir / "snapshots").resolve()
        if (
            representative_image.parent != snapshot_directory
            or not representative_image.is_file()
        ):
            raise StoryGenerationError(
                "Codex selected an image outside this session's snapshots."
            )

        story_path = session_dir / "story.json"
        story_path.write_text(
            json.dumps(document, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return StoryResult(
            title=document["title"],
            story=document["story"],
            representative_image=representative_image,
        )

    def _build_command(
        self,
        session_dir: Path,
        snapshot_paths: tuple[Path, ...],
    ) -> list[str]:
        schema_path = Path(__file__).with_name("story_schema.json")
        command = [
            self._executable,
            "exec",
            "--ephemeral",
            "--skip-git-repo-check",
            "--cd",
            str(session_dir),
            "--sandbox",
            "read-only",
            "--color",
            "never",
            "--output-schema",
            str(schema_path),
        ]
        for snapshot_path in snapshot_paths:
            command.extend(("--image", str(snapshot_path)))
        command.append("-")
        return command

    @staticmethod
    def _build_prompt(events_text: str) -> str:
        return (
            "Create a short creative story based only on the objects actually found "
            "in these session snapshots. Use the instruction and detection timeline "
            "below. Keep the story presentation-friendly: 2 to 4 sentences. Select "
            "exactly one representative_image using a snapshot path exactly as it "
            "appears in the event data. Return only the requested JSON object.\n\n"
            f"events.json:\n{events_text}"
        )


def _parse_story_document(output: str) -> dict[str, str]:
    try:
        value: Any = json.loads(output.strip())
    except json.JSONDecodeError as error:
        raise StoryGenerationError("Codex returned invalid story JSON.") from error

    if not isinstance(value, dict):
        raise StoryGenerationError("Codex story output must be a JSON object.")

    required = ("title", "story", "representative_image")
    if any(
        not isinstance(value.get(key), str) or not value[key].strip()
        for key in required
    ):
        raise StoryGenerationError("Codex story JSON is missing required text fields.")
    return {key: value[key].strip() for key in required}
