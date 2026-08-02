"""Command-line interface for prompt-guided SAM-Audio separation."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import create_sound_separator


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Separate a described sound with SAM-Audio on Apple Silicon.",
    )
    parser.add_argument("audio_file", type=Path, help="Path to the mixed audio file")
    parser.add_argument(
        "--prompt",
        required=True,
        help='Sound to isolate, such as "dog barking"',
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/sam_audio"),
        help="Directory for target and residual WAV files",
    )
    return parser.parse_args()


def main() -> None:
    """Run separation and print paths and runtime measurements."""
    args = _parse_args()
    with create_sound_separator() as separator:
        result = separator.separate_file(
            args.audio_file,
            prompt=args.prompt,
            output_dir=args.output_dir,
        )

    print(f"target: {result.target_path}")
    print(f"residual: {result.residual_path}")
    print(f"elapsed_seconds: {result.elapsed_seconds:.3f}")
    if result.peak_memory_gb is not None:
        print(f"peak_memory_gb: {result.peak_memory_gb:.3f}")


if __name__ == "__main__":
    main()
