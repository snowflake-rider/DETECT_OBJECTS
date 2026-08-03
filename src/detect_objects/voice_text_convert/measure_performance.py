"""Benchmark Korean transcription accuracy and latency across Whisper models."""

from __future__ import annotations

import gc
import re
import time
from typing import Any

import numpy as np
import sounddevice as sd
import torch
import whisper

SAMPLE_RATE = 16_000
CHANNELS = 1
RECORD_SECONDS = 5

# Compare the checkpoints selected by the VAD refactor on main.
MODEL_NAMES = ["base", "small", "medium", "large", "turbo"]

REFERENCE_TEXT = "폰과 사람을 찾아줘"
BENCHMARK_REPEAT = 3


def record_audio() -> np.ndarray:
    """Record one reference utterance shared by every model benchmark."""
    print(f"\n{RECORD_SECONDS}초 동안 녹음합니다.")
    print(f'다음 문장을 말해보세요: "{REFERENCE_TEXT}"')

    audio = sd.rec(
        frames=int(RECORD_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        blocking=True,
    ).reshape(-1)

    max_amplitude = float(np.max(np.abs(audio)))
    print("녹음 완료")
    print(f"최대 진폭: {max_amplitude:.6f}")

    if max_amplitude < 0.001:
        raise RuntimeError(
            "마이크 입력이 너무 작습니다. 마이크 권한과 입력 장치를 확인하세요."
        )

    return audio


def normalize_text(text: str) -> str:
    """Remove whitespace and punctuation before calculating Korean CER."""
    text = text.lower()
    text = re.sub(r"\s+", "", text)
    return re.sub(r"[^\w가-힣]", "", text)


def levenshtein_distance(reference: str, hypothesis: str) -> int:
    """Return the insertion, deletion, and substitution edit distance."""
    rows = len(reference) + 1
    columns = len(hypothesis) + 1
    distance = [[0 for _ in range(columns)] for _ in range(rows)]

    for row in range(rows):
        distance[row][0] = row
    for column in range(columns):
        distance[0][column] = column

    for row in range(1, rows):
        for column in range(1, columns):
            cost = int(reference[row - 1] != hypothesis[column - 1])
            distance[row][column] = min(
                distance[row - 1][column] + 1,
                distance[row][column - 1] + 1,
                distance[row - 1][column - 1] + cost,
            )

    return distance[-1][-1]


def calculate_cer(reference: str, hypothesis: str) -> float:
    """Calculate character error rate; lower values are more accurate."""
    normalized_reference = normalize_text(reference)
    normalized_hypothesis = normalize_text(hypothesis)

    if not normalized_reference:
        return 0.0 if not normalized_hypothesis else 1.0

    return levenshtein_distance(
        normalized_reference,
        normalized_hypothesis,
    ) / len(normalized_reference)


def select_device() -> str:
    """Use CUDA when available and CPU otherwise."""
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def synchronize_device(device: str) -> None:
    """Synchronize asynchronous CUDA work before recording a duration."""
    if device == "cuda":
        torch.cuda.synchronize()


def release_model(model: Any, device: str) -> None:
    """Release one model before loading the next benchmark checkpoint."""
    del model
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()


def benchmark_model(
    model_name: str,
    audio: np.ndarray,
    device: str,
) -> dict[str, Any]:
    """Load, warm up, and repeatedly benchmark one Whisper checkpoint."""
    print("\n" + "=" * 60)
    print(f"모델: {model_name}")
    print("=" * 60)

    load_started_at = time.perf_counter()
    model = None

    try:
        model = whisper.load_model(model_name, device=device)
        synchronize_device(device)
        load_time = time.perf_counter() - load_started_at
        print(f"모델 로딩 시간: {load_time:.3f}초")

        print("워밍업 추론 중...")
        warmup_result = model.transcribe(
            audio,
            language="ko",
            task="transcribe",
            fp16=device == "cuda",
            verbose=False,
        )
        synchronize_device(device)
        print("워밍업 결과:", warmup_result.get("text", "").strip())

        inference_times: list[float] = []
        recognized_texts: list[str] = []

        for repeat_index in range(BENCHMARK_REPEAT):
            synchronize_device(device)
            started_at = time.perf_counter()
            result = model.transcribe(
                audio,
                language="ko",
                task="transcribe",
                fp16=device == "cuda",
                verbose=False,
            )
            synchronize_device(device)

            inference_time = time.perf_counter() - started_at
            recognized_text = result.get("text", "").strip()
            inference_times.append(inference_time)
            recognized_texts.append(recognized_text)
            print(
                f"{repeat_index + 1}회차: "
                f"{inference_time:.3f}초 / "
                f'"{recognized_text}"'
            )

        average_inference_time = float(np.mean(inference_times))
        minimum_inference_time = float(np.min(inference_times))
        final_text = recognized_texts[-1]

        return {
            "model": model_name,
            "load_time": load_time,
            "average_inference_time": average_inference_time,
            "minimum_inference_time": minimum_inference_time,
            "real_time_factor": average_inference_time / RECORD_SECONDS,
            "cer": calculate_cer(REFERENCE_TEXT, final_text),
            "text": final_text,
        }
    finally:
        if model is not None:
            release_model(model, device)


def print_summary(results: list[dict[str, Any]]) -> None:
    """Print one comparison table for all successful model benchmarks."""
    print("\n")
    print("=" * 100)
    print("Whisper 모델 성능 비교")
    print("=" * 100)
    print(
        f"{'Model':<10}"
        f"{'Load(s)':>10}"
        f"{'Avg(s)':>10}"
        f"{'Min(s)':>10}"
        f"{'RTF':>10}"
        f"{'CER':>10}"
        "  Result"
    )
    print("-" * 100)

    for result in results:
        print(
            f"{result['model']:<10}"
            f"{result['load_time']:>10.3f}"
            f"{result['average_inference_time']:>10.3f}"
            f"{result['minimum_inference_time']:>10.3f}"
            f"{result['real_time_factor']:>10.3f}"
            f"{result['cer']:>10.3f}"
            f"  {result['text']}"
        )


def main() -> None:
    """Record one phrase and compare every configured Whisper model."""
    device = select_device()
    print(f"측정 장치: {device}")
    print(f"비교 모델: {MODEL_NAMES}")

    audio = record_audio()
    results: list[dict[str, Any]] = []

    for model_name in MODEL_NAMES:
        try:
            results.append(
                benchmark_model(
                    model_name=model_name,
                    audio=audio,
                    device=device,
                )
            )
        except Exception as error:
            print(f"{model_name} 모델 측정 실패: " f"{type(error).__name__}: {error}")

    print_summary(results)


if __name__ == "__main__":
    main()
