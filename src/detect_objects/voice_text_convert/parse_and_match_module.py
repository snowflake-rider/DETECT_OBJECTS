"""Match Korean aliases and English YOLO names in user instructions."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Self


@dataclass(frozen=True)
class DetectedClass:
    korean_word: str
    index: int
    yolo_class: str


class Text_Manager:
    """Load supported object names and find them in voice or typed text."""

    def __init__(self) -> None:
        self.__dictionary: dict[str, dict[str, object]] = {}
        self.__dictionary_list: list[tuple[str, dict[str, object]]] = []

    @staticmethod
    def _normalize(text: str) -> str:
        if not isinstance(text, str):
            raise RuntimeError("string 이 아닌 데이터")
        return text.lower().replace(" ", "").strip()

    @classmethod
    def _find_alias(cls, text: str, alias: str) -> int:
        """Find an alias without matching English names inside other words."""
        if alias.isascii():
            words = [re.escape(word) for word in alias.lower().split()]
            pattern = r"(?<![a-z0-9])" + r"\s+".join(words) + r"(?![a-z0-9])"
            match = re.search(pattern, text.lower())
            return -1 if match is None else match.start()

        return cls._normalize(text).find(cls._normalize(alias))

    @staticmethod
    def _read_dictionary(path: Path) -> dict[str, dict[str, object]]:
        try:
            with path.open("r", encoding="utf-8") as dictionary_file:
                dictionary = json.load(dictionary_file)
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Could not load class dictionary: {path}") from error

        if not isinstance(dictionary, dict):
            raise RuntimeError(f"Class dictionary must be an object: {path}")
        return dictionary

    @staticmethod
    def _validate_entry(alias: str, data: dict[str, object]) -> None:
        class_name = data.get("class_name")
        class_id = data.get("class_id")
        if not isinstance(class_name, str) or not isinstance(class_id, int):
            raise RuntimeError(f"Invalid class dictionary entry: {alias}={data}")

    def _load_class_dictionary(self) -> None:
        dictionary_dir = Path(__file__).resolve().parent
        korean_dictionary = self._read_dictionary(
            dictionary_dir / "korean_class_names.json"
        )
        class_catalog = self._read_dictionary(dictionary_dir / "class_names.json")

        english_dictionary: dict[str, dict[str, object]] = {}
        for data in class_catalog.values():
            if not isinstance(data, dict):
                raise RuntimeError(f"Invalid class dictionary entry: {data}")
            self._validate_entry("English class", data)
            class_name = data["class_name"]
            english_dictionary[str(class_name)] = data

        self.__dictionary = {**english_dictionary, **korean_dictionary}
        for alias, data in self.__dictionary.items():
            if not isinstance(data, dict):
                raise RuntimeError(f"Invalid class dictionary entry: {alias}={data}")
            self._validate_entry(alias, data)

        self.__dictionary_list = sorted(
            self.__dictionary.items(),
            key=lambda item: len(self._normalize(item[0])),
            reverse=True,
        )

    def __enter__(self) -> Self:
        self._load_class_dictionary()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        """Close the parser context; dictionaries require no cleanup."""

    def get_supported_yolo_classes(self) -> list[str]:
        """Return unique YOLO class names available to the text parser."""
        if not isinstance(self.__dictionary, dict) or not self.__dictionary:
            raise RuntimeError("클래스 사전이 로드되지 않았습니다")

        return list(
            dict.fromkeys(
                data["class_name"]
                for data in self.__dictionary.values()
                if isinstance(data, dict) and isinstance(data.get("class_name"), str)
            )
        )

    def extract(self, text: str) -> list[DetectedClass]:
        """Return each unique supported object mentioned in the text."""
        self._normalize(text)
        if not self.__dictionary:
            raise ValueError("invalid dictionary")
        found_yolo_classes: set[str] = set()
        positioned_classes: list[tuple[int, DetectedClass]] = []
        for key, data in self.__dictionary_list:
            match_position = self._find_alias(text, key)
            if match_position < 0:
                continue
            class_name = data.get("class_name")
            class_id = data.get("class_id")
            if not isinstance(class_name, str) or not isinstance(class_id, int):
                raise ValueError(f"잘못된 클래스 데이터입니다: {key}={data}")
            if class_name in found_yolo_classes:
                continue
            positioned_classes.append(
                (
                    match_position,
                    DetectedClass(
                        korean_word=key,
                        yolo_class=class_name,
                        index=class_id,
                    ),
                )
            )
            found_yolo_classes.add(class_name)

        positioned_classes.sort(key=lambda item: item[0])
        return [detected for _, detected in positioned_classes]


if __name__ == "__main__":
    try:
        with Text_Manager() as manager:
            class_list = manager.extract("백팩을 맨 사람")
            print(class_list)
    except Exception as e:
        print(e)
