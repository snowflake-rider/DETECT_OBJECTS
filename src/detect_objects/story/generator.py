"""Generate a structured visual story with the locally authenticated Codex CLI."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from io import BytesIO
import json
import os
from pathlib import Path
import shlex
import shutil
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


@dataclass(frozen=True)
class StoryInputs:
    """Selected crop files and matching event data sent to Codex."""

    crop_paths: tuple[Path, ...]
    events_text: str


class StoryGenerator(Protocol):
    """Story generation boundary used by the Desktop worker."""

    def generate(self, session_dir: Path) -> StoryResult: ...


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
BinaryCommandRunner = Callable[..., subprocess.CompletedProcess[bytes]]


def _find_codex_executable() -> str:
    """Find Codex even when a GUI-launched app has a minimal PATH."""
    configured = os.environ.get("ODIA_CODEX_EXECUTABLE", "").strip()
    if configured:
        return str(Path(configured).expanduser())

    discovered = shutil.which("codex")
    if discovered:
        return discovered

    candidates = (
        Path.home() / ".local" / "bin" / "codex",
        Path("/opt/homebrew/bin/codex"),
        Path("/usr/local/bin/codex"),
    )
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return "codex"


def _codex_environment(executable: str) -> dict[str, str]:
    """Expose Codex's directory so env-based Node launchers can find Node."""
    environment = os.environ.copy()
    executable_path = Path(executable).expanduser()
    if executable_path.parent == Path("."):
        return environment

    executable_directory = str(executable_path.parent)
    path_entries = environment.get("PATH", "").split(os.pathsep)
    if executable_directory not in path_entries:
        environment["PATH"] = os.pathsep.join(
            (executable_directory, *filter(None, path_entries))
        )
    return environment


class CodexStoryGenerator:
    """Send selected object crops and session events to ``codex exec``."""

    def __init__(
        self,
        *,
        executable: str | None = None,
        timeout_seconds: float = 120.0,
        runner: CommandRunner = subprocess.run,
    ) -> None:
        self._executable = executable or _find_codex_executable()
        self._timeout_seconds = timeout_seconds
        self._runner = runner

    def generate(self, session_dir: Path) -> StoryResult:
        """Generate and persist one story for a completed or active session."""
        events_path = session_dir / "events.json"
        if not events_path.is_file():
            raise StoryGenerationError(f"Session events were not found: {events_path}")

        inputs = _load_story_inputs(session_dir, events_path)
        command = self._build_command(session_dir, inputs.crop_paths)
        try:
            completed = self._runner(
                command,
                input=self._build_prompt(inputs.events_text),
                capture_output=True,
                text=True,
                env=_codex_environment(self._executable),
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
        representative_image = _selected_representative_image(
            session_dir,
            document["representative_image"],
            inputs.crop_paths,
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
        crop_paths: tuple[Path, ...],
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
        for crop_path in crop_paths:
            command.extend(("--image", str(crop_path)))
        command.append("-")
        return command

    @staticmethod
    def _build_prompt(events_text: str) -> str:
        return (
            "Create a short creative story based only on the selected object crops. "
            "Use the instruction and filtered detection timeline "
            "below. Write the title and story in natural Korean. The story must "
            "begin with exactly this sentence: \"제가 이 사진들을 보고 짧은 이야기를 "
            "만들어 봤어요.\" Follow it with 2 to 3 short, creative sentences that "
            "are easy to present aloud. Select exactly one representative_image "
            "using a crop path exactly as it appears in the event data. Return "
            "only the requested JSON object.\n\n"
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

        inputs = _load_story_inputs(session_dir, events_path)
        archive = self._build_archive(
            events_path,
            inputs.crop_paths,
            CodexStoryGenerator._build_prompt(inputs.events_text),
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
        representative_image = _selected_representative_image(
            session_dir,
            document["representative_image"],
            inputs.crop_paths,
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
        crop_paths: tuple[Path, ...],
        prompt: str,
    ) -> bytes:
        archive_buffer = BytesIO()
        with tarfile.open(fileobj=archive_buffer, mode="w:gz") as archive:
            archive.add(events_path, arcname="events.json", recursive=False)
            session_dir = events_path.parent.resolve()
            for crop_path in crop_paths:
                archive.add(
                    crop_path,
                    arcname=crop_path.resolve().relative_to(session_dir).as_posix(),
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
        executable_path = Path(self._remote_executable)
        path_setup = ""
        if executable_path.parent != Path("."):
            executable_directory = shlex.quote(str(executable_path.parent))
            path_setup = f"PATH={executable_directory}:$PATH\nexport PATH\n"
        return f"""set -eu
{path_setup}story_root=$(mktemp -d "${{TMPDIR:-/tmp}}/odia-story.XXXXXX")
cleanup() {{ rm -rf -- "$story_root"; }}
trap cleanup EXIT HUP INT TERM
tar -xzf - -C "$story_root"
set --
for story_image in "$story_root"/crops/*.png "$story_root"/snapshots/*.png; do
    [ -f "$story_image" ] || continue
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


def _load_story_inputs(session_dir: Path, events_path: Path) -> StoryInputs:
    """Load only the displayed crops selected in the persisted Story queue."""
    try:
        document: Any = json.loads(events_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise StoryGenerationError("Session events contain invalid JSON.") from error
    if not isinstance(document, dict) or not isinstance(
        document.get("detections"), list
    ):
        raise StoryGenerationError("Session events must contain a detection list.")

    selected_events: list[dict[str, Any]] = []
    crop_paths: list[Path] = []
    resolved_session = session_dir.resolve()
    for event in document["detections"]:
        if not isinstance(event, dict) or event.get("selected", True) is not True:
            continue
        relative_value = event.get("crop", event.get("snapshot"))
        if not isinstance(relative_value, str) or not relative_value.strip():
            raise StoryGenerationError("A selected detection is missing its crop path.")
        relative_path = Path(relative_value)
        if (
            relative_path.is_absolute()
            or len(relative_path.parts) != 2
            or relative_path.parts[0] not in {"crops", "snapshots"}
        ):
            raise StoryGenerationError("A selected crop path is outside this session.")
        crop_path = (session_dir / relative_path).resolve()
        try:
            crop_path.relative_to(resolved_session)
        except ValueError as error:
            raise StoryGenerationError(
                "A selected crop path is outside this session."
            ) from error
        if not crop_path.is_file():
            raise StoryGenerationError(
                f"Selected object crop was not found: {crop_path}"
            )
        selected_events.append(event)
        crop_paths.append(crop_path)

    if not crop_paths:
        raise StoryGenerationError(
            "Select at least one object crop for the Story queue."
        )

    filtered_document = dict(document)
    filtered_document["detections"] = selected_events
    return StoryInputs(
        crop_paths=tuple(crop_paths),
        events_text=json.dumps(filtered_document, ensure_ascii=False, indent=2),
    )


def _selected_representative_image(
    session_dir: Path,
    relative_value: str,
    crop_paths: tuple[Path, ...],
) -> Path:
    representative_image = (session_dir / relative_value).resolve()
    if representative_image not in crop_paths:
        raise StoryGenerationError(
            "Codex selected an image outside the selected Story crop queue."
        )
    return representative_image


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
