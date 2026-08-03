"""Behavior tests for generating one story from a recorded session."""

from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from detect_objects.story.generator import (
    CodexStoryGenerator,
    SshCodexStoryGenerator,
    create_story_generator,
)


class RecordingRunner:
    def __init__(self, response: dict[str, str]) -> None:
        self.response = response
        self.arguments: list[str] = []
        self.prompt = ""

    def __call__(self, arguments, **options):
        self.arguments = list(arguments)
        self.prompt = options["input"]
        return subprocess.CompletedProcess(
            arguments,
            0,
            stdout=json.dumps(self.response, ensure_ascii=False),
            stderr="",
        )


class RecordingSshRunner:
    def __init__(self, response: dict[str, str]) -> None:
        self.response = response
        self.arguments: list[str] = []
        self.archive_names: set[str] = set()
        self.prompt = ""

    def __call__(self, arguments, **options):
        self.arguments = list(arguments)
        with tarfile.open(fileobj=BytesIO(options["input"]), mode="r:gz") as archive:
            self.archive_names = set(archive.getnames())
            prompt_file = archive.extractfile("prompt.txt")
            self.prompt = prompt_file.read().decode("utf-8")
        return subprocess.CompletedProcess(
            arguments,
            0,
            stdout=json.dumps(self.response, ensure_ascii=False).encode("utf-8"),
            stderr=b"",
        )


class CodexStoryGeneratorTests(unittest.TestCase):
    def test_setup_environment_selects_the_remote_codex_host(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "ODIA_CODEX_SSH_TARGET": "codex-mac",
                "ODIA_CODEX_REMOTE_EXECUTABLE": "/opt/homebrew/bin/codex",
            },
            clear=False,
        ):
            generator = create_story_generator()

        self.assertIsInstance(generator, SshCodexStoryGenerator)

    def test_session_images_and_events_produce_persisted_story(self) -> None:
        runner = RecordingRunner(
            {
                "title": "The Watchful Street",
                "story": "A person and a bicycle crossed paths under a patient clock.",
                "representative_image": "crops/person.png",
            }
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            session_dir = Path(temporary_directory)
            crops_dir = session_dir / "crops"
            crops_dir.mkdir()
            first_crop = crops_dir / "person.png"
            second_crop = crops_dir / "bicycle.png"
            first_crop.write_bytes(b"first image")
            second_crop.write_bytes(b"second image")
            events = {
                "instructions": [{"text": "사람과 자전거를 찾아줘"}],
                "detections": [
                    {"crop": "crops/person.png", "selected": True},
                    {"crop": "crops/bicycle.png", "selected": False},
                ],
            }
            (session_dir / "events.json").write_text(
                json.dumps(events, ensure_ascii=False),
                encoding="utf-8",
            )

            result = CodexStoryGenerator(runner=runner).generate(session_dir)

            self.assertEqual(result.title, "The Watchful Street")
            self.assertEqual(
                result.story,
                "A person and a bicycle crossed paths under a patient clock.",
            )
            self.assertEqual(result.representative_image, first_crop.resolve())
            self.assertEqual(
                json.loads((session_dir / "story.json").read_text(encoding="utf-8")),
                runner.response,
            )
            self.assertEqual(runner.arguments.count("--image"), 1)
            self.assertIn(str(first_crop.resolve()), runner.arguments)
            self.assertNotIn(str(second_crop.resolve()), runner.arguments)
            self.assertIn("--output-schema", runner.arguments)
            self.assertEqual(
                runner.arguments[runner.arguments.index("--cd") + 1],
                str(session_dir),
            )
            self.assertIn("read-only", runner.arguments)
            self.assertNotIn("--ask-for-approval", runner.arguments)
            self.assertIn("사람과 자전거를 찾아줘", runner.prompt)
            self.assertIn("short creative story", runner.prompt)
            self.assertIn("Write the title and story in natural Korean", runner.prompt)
            self.assertIn(
                "제가 이 사진들을 보고 짧은 이야기를 만들어 봤어요.",
                runner.prompt,
            )
            self.assertIn("2 to 3 short, creative sentences", runner.prompt)
            self.assertNotIn("crops/bicycle.png", runner.prompt)

    def test_finds_codex_and_its_runtime_when_app_path_is_restricted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            local_bin = root / ".local" / "bin"
            local_bin.mkdir(parents=True)
            codex = local_bin / "codex"
            codex.write_text("#!/usr/bin/env codex-test-runtime\n", encoding="utf-8")
            codex.chmod(0o755)
            runtime = local_bin / "codex-test-runtime"
            runtime.write_text(
                "#!/bin/sh\n"
                'printf \'%s\\n\' \'{"title":"Found","story":"It worked.",'
                '"representative_image":"crops/object.png"}\'\n',
                encoding="utf-8",
            )
            runtime.chmod(0o755)

            session_dir = root / "session"
            crops_dir = session_dir / "crops"
            crops_dir.mkdir(parents=True)
            crop = crops_dir / "object.png"
            crop.write_bytes(b"image")
            (session_dir / "events.json").write_text(
                json.dumps(
                    {
                        "instructions": [],
                        "detections": [
                            {
                                "crop": "crops/object.png",
                                "selected": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict(
                "os.environ",
                {
                    "HOME": str(root),
                    "PATH": "/usr/bin:/bin",
                    "ODIA_CODEX_SSH_TARGET": "",
                },
                clear=False,
            ):
                result = create_story_generator().generate(session_dir)

            self.assertEqual(result.title, "Found")
            self.assertEqual(result.representative_image, crop.resolve())

    def test_session_can_generate_a_story_through_a_remote_codex_host(self) -> None:
        runner = RecordingSshRunner(
            {
                "title": "The Remote Lookout",
                "story": "A watchful person crossed the frame from miles away.",
                "representative_image": "snapshots/person.png",
            }
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            session_dir = Path(temporary_directory)
            snapshots_dir = session_dir / "snapshots"
            snapshots_dir.mkdir()
            snapshot = snapshots_dir / "person.png"
            snapshot.write_bytes(b"remote image")
            (session_dir / "events.json").write_text(
                json.dumps(
                    {
                        "instructions": [{"text": "사람을 찾아줘"}],
                        "detections": [
                            {"snapshot": "snapshots/person.png"},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = SshCodexStoryGenerator(
                ssh_target="codex-mac",
                remote_executable="/opt/homebrew/bin/codex",
                runner=runner,
            ).generate(session_dir)

            self.assertEqual(result.title, "The Remote Lookout")
            self.assertEqual(result.representative_image, snapshot.resolve())
            self.assertEqual(runner.arguments[0], "ssh")
            self.assertIn("codex-mac", runner.arguments)
            self.assertIn("/opt/homebrew/bin/codex", runner.arguments[-1])
            self.assertIn("PATH=/opt/homebrew/bin:$PATH", runner.arguments[-1])
            self.assertIn("read-only", runner.arguments[-1])
            self.assertEqual(
                runner.archive_names,
                {
                    "events.json",
                    "prompt.txt",
                    "snapshots/person.png",
                    "story_schema.json",
                },
            )
            self.assertIn("사람을 찾아줘", runner.prompt)
            self.assertIn(
                "제가 이 사진들을 보고 짧은 이야기를 만들어 봤어요.",
                runner.prompt,
            )
            self.assertEqual(
                json.loads((session_dir / "story.json").read_text(encoding="utf-8")),
                runner.response,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
