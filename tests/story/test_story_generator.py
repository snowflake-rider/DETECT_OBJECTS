"""Behavior tests for generating one story from a recorded session."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from detect_objects.story.generator import CodexStoryGenerator


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


class CodexStoryGeneratorTests(unittest.TestCase):
    def test_session_images_and_events_produce_persisted_story(self) -> None:
        runner = RecordingRunner(
            {
                "title": "The Watchful Street",
                "story": "A person and a bicycle crossed paths under a patient clock.",
                "representative_image": "snapshots/person.png",
            }
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            session_dir = Path(temporary_directory)
            snapshots_dir = session_dir / "snapshots"
            snapshots_dir.mkdir()
            first_snapshot = snapshots_dir / "person.png"
            second_snapshot = snapshots_dir / "bicycle.png"
            first_snapshot.write_bytes(b"first image")
            second_snapshot.write_bytes(b"second image")
            events = {
                "instructions": [{"text": "사람과 자전거를 찾아줘"}],
                "detections": [
                    {"snapshot": "snapshots/person.png"},
                    {"snapshot": "snapshots/bicycle.png"},
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
            self.assertEqual(result.representative_image, first_snapshot.resolve())
            self.assertEqual(
                json.loads((session_dir / "story.json").read_text(encoding="utf-8")),
                runner.response,
            )
            self.assertEqual(runner.arguments.count("--image"), 2)
            self.assertIn(str(first_snapshot), runner.arguments)
            self.assertIn(str(second_snapshot), runner.arguments)
            self.assertIn("--output-schema", runner.arguments)
            self.assertEqual(
                runner.arguments[runner.arguments.index("--cd") + 1],
                str(session_dir),
            )
            self.assertIn("read-only", runner.arguments)
            self.assertNotIn("--ask-for-approval", runner.arguments)
            self.assertIn("사람과 자전거를 찾아줘", runner.prompt)
            self.assertIn("short creative story", runner.prompt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
