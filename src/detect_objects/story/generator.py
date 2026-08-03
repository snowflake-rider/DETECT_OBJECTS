"""Generate a structured visual story with the locally authenticated Codex CLI."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from io import BytesIO
import json
import os
from pathlib import Path
import shlex
import subprocess
import tarfile
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
BinaryCommandRunner = Callable[..., subprocess.CompletedProcess[bytes]]


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


class SshCodexStoryGenerator:
    """Stream a story session to a separately authenticated Codex host."""

    def __init__(
        self,
        *,
        ssh_target: str,
        remote_executable: str = "codex",
        timeout_seconds: float = 120.0,
        runner: BinaryCommandRunner = subprocess.run,
    ) -> None:
        if not ssh_target.strip() or ssh_target.startswith("-"):
            raise ValueError("ssh_target must be an SSH alias or user@host")
        self._ssh_target = ssh_target
        self._remote_executable = remote_executable
        self._timeout_seconds = timeout_seconds
        self._runner = runner

    def generate(self, session_dir: Path) -> StoryResult:
        """Generate a local StoryResult through an SSH-connected Codex CLI."""
        events_path = session_dir / "events.json"
        if not events_path.is_file():
            raise StoryGenerationError(f"Session events were not found: {events_path}")

        snapshot_paths = tuple(sorted((session_dir / "snapshots").glob("*.png")))
        if not snapshot_paths:
            raise StoryGenerationError("No matching snapshots are available yet.")

        events_text = events_path.read_text(encoding="utf-8")
        archive = self._build_archive(
            events_path,
            snapshot_paths,
            CodexStoryGenerator._build_prompt(events_text),
        )
        command = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=10",
            self._ssh_target,
            self._remote_command(),
        ]
        try:
            completed = self._runner(
                command,
                input=archive,
                capture_output=True,
                timeout=self._timeout_seconds,
                check=False,
            )
        except FileNotFoundError as error:
            raise StoryGenerationError(
                "SSH was not found on the project machine."
            ) from error
        except subprocess.TimeoutExpired as error:
            raise StoryGenerationError(
                "Remote Codex story generation timed out."
            ) from error

        stdout = _decode_output(completed.stdout)
        stderr = _decode_output(completed.stderr)
        if completed.returncode != 0:
            detail = stderr.strip() or "SSH exited without an error message."
            raise StoryGenerationError(
                f"Remote Codex story generation failed: {detail}"
            )

        document = _parse_story_document(stdout)
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

        (session_dir / "story.json").write_text(
            json.dumps(document, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return StoryResult(
            title=document["title"],
            story=document["story"],
            representative_image=representative_image,
        )

    @staticmethod
    def _build_archive(
        events_path: Path,
        snapshot_paths: tuple[Path, ...],
        prompt: str,
    ) -> bytes:
        archive_buffer = BytesIO()
        with tarfile.open(fileobj=archive_buffer, mode="w:gz") as archive:
            archive.add(events_path, arcname="events.json", recursive=False)
            for snapshot_path in snapshot_paths:
                archive.add(
                    snapshot_path,
                    arcname=f"snapshots/{snapshot_path.name}",
                    recursive=False,
                )
            archive.add(
                Path(__file__).with_name("story_schema.json"),
                arcname="story_schema.json",
                recursive=False,
            )
            prompt_bytes = prompt.encode("utf-8")
            prompt_info = tarfile.TarInfo("prompt.txt")
            prompt_info.size = len(prompt_bytes)
            archive.addfile(prompt_info, BytesIO(prompt_bytes))
        return archive_buffer.getvalue()

    def _remote_command(self) -> str:
        executable = shlex.quote(self._remote_executable)
        return f"""set -eu
story_root=$(mktemp -d "${{TMPDIR:-/tmp}}/odia-story.XXXXXX")
cleanup() {{ rm -rf -- "$story_root"; }}
trap cleanup EXIT HUP INT TERM
tar -xzf - -C "$story_root"
set --
for story_image in "$story_root"/snapshots/*.png; do
    set -- "$@" --image "$story_image"
done
{executable} exec --ephemeral --skip-git-repo-check \
    --cd "$story_root" --sandbox read-only --color never \
    --output-schema "$story_root/story_schema.json" "$@" - \
    < "$story_root/prompt.txt"
"""


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


def _decode_output(output: bytes | str) -> str:
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return output


def create_story_generator() -> StoryGenerator:
    """Choose local or SSH Codex from the setup process environment."""
    ssh_target = os.environ.get("ODIA_CODEX_SSH_TARGET", "").strip()
    if ssh_target:
        return SshCodexStoryGenerator(
            ssh_target=ssh_target,
            remote_executable=os.environ.get(
                "ODIA_CODEX_REMOTE_EXECUTABLE",
                "codex",
            ),
        )
    return CodexStoryGenerator()
