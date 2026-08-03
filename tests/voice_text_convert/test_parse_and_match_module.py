"""Tests for matching voice and typed object instructions."""

from __future__ import annotations

import unittest

from detect_objects.voice_text_convert.parse_and_match_module import Text_Manager


class TextManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manager_context = Text_Manager()
        self.manager = self.manager_context.__enter__()

    def tearDown(self) -> None:
        self.manager_context.__exit__(None, None, None)

    def test_matches_english_yolo_class_names(self) -> None:
        matches = self.manager.extract("find person and bicycle")

        self.assertEqual(
            [match.yolo_class for match in matches],
            ["person", "bicycle"],
        )

    def test_keeps_matching_korean_object_names(self) -> None:
        matches = self.manager.extract("사람과 자전거를 찾아줘")

        self.assertEqual(
            [match.yolo_class for match in matches],
            ["person", "bicycle"],
        )

    def test_supported_classes_are_unique_across_languages(self) -> None:
        supported_classes = self.manager.get_supported_yolo_classes()

        self.assertEqual(len(supported_classes), len(set(supported_classes)))
        self.assertIn("person", supported_classes)
        self.assertIn("bicycle", supported_classes)

    def test_does_not_match_english_class_names_inside_other_words(self) -> None:
        matches = self.manager.extract("locate person near the scarf")

        self.assertEqual(
            [match.yolo_class for match in matches],
            ["person"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
