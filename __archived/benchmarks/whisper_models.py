import gc
import re
import time

import numpy as np
import sounddevice as sd
import torch
import whisper


SAMPLE_RATE = 16_000
CHANNELS = 1
RECORD_SECONDS = 5

# 처음에는 무리하지 말고 이 세 모델로 비교하는 것을 추천
MODEL_NAMES = [
    "tiny",
    "base",
    "small",
]

# 실제로 마이크에 말할 문장
REFERENCE_TEXT = "폰과 사람을 찾아줘"

# 첫 실행 이후 반복 측정 횟수
BENCHMARK_REPEAT = 3


def record_audio() -> np.ndarray:
    print(f"\n{RECORD_SECONDS}초 동안 녹음합니다.")
    print(f'다음 문장을 말해보세요: "{REFERENCE_TEXT}"')

    audio = sd.rec(
        frames=int(RECORD_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        blocking=True,
    )

    audio = audio.reshape(-1)

    max_amplitude = float(np.max(np.abs(audio)))

    print("녹음 완료")
    print(f"최대 진폭: {max_amplitude:.6f}")

    if max_amplitude < 0.001:
        raise RuntimeError(
            "마이크 입력이 너무 작습니다. 마이크 권한과 입력 장치를 확인하세요."
        )

    return audio


def normalize_text(text: str) -> str:
    """
    CER 계산 전에 공백과 문장부호를 제거한다.

    예:
        '폰과 사람을 찾아줘.' -> '폰과사람을찾아줘'
    """
    text = text.lower()
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[^\w가-힣]", "", text)

    return text


def levenshtein_distance(
    reference: str,
    hypothesis: str,
) -> int:
    """
    두 문자열 사이의 편집 거리 계산.

    삽입, 삭제, 교체가 각각 몇 번 필요한지 계산한다.
    """
    rows = len(reference) + 1
    columns = len(hypothesis) + 1

    dp = [[0 for _ in range(columns)] for _ in range(rows)]

    for row in range(rows):
        dp[row][0] = row

    for column in range(columns):
        dp[0][column] = column

    for row in range(1, rows):
        for column in range(1, columns):
            if reference[row - 1] == hypothesis[column - 1]:
                cost = 0
            else:
                cost = 1

            dp[row][column] = min(
                dp[row - 1][column] + 1,  # 삭제
                dp[row][column - 1] + 1,  # 삽입
                dp[row - 1][column - 1] + cost,  # 교체
            )

    return dp[-1][-1]


def calculate_cer(
    reference: str,
    hypothesis: str,
) -> float:
    """
    Character Error Rate.

    0.0이면 완전히 일치한다.
    값이 낮을수록 정확하다.
    """
    normalized_reference = normalize_text(reference)
    normalized_hypothesis = normalize_text(hypothesis)

    if not normalized_reference:
        return 0.0 if not normalized_hypothesis else 1.0

    distance = levenshtein_distance(
        normalized_reference,
        normalized_hypothesis,
    )

    return distance / len(normalized_reference)


def select_device() -> str:
    """
    OpenAI Whisper 원본 구현은 환경에 따라 MPS에서
    일부 연산 문제가 발생할 수 있으므로 우선 CPU로 측정한다.

    NVIDIA 환경이라면 CUDA를 사용한다.
    """
    if torch.cuda.is_available():
        return "cuda"

    return "cpu"


def synchronize_device(device: str) -> None:
    """
    GPU 연산은 비동기일 수 있으므로 시간 측정 전에 동기화한다.
    """
    if device == "cuda":
        torch.cuda.synchronize()


def release_model(
    model,
    device: str,
) -> None:
    del model
    gc.collect()

    if device == "cuda":
        torch.cuda.empty_cache()


def benchmark_model(
    model_name: str,
    audio: np.ndarray,
    device: str,
) -> dict:
    print("\n" + "=" * 60)
    print(f"모델: {model_name}")
    print("=" * 60)

    # 최초 다운로드 시간도 포함될 수 있음
    load_started_at = time.perf_counter()

    model = whisper.load_model(
        model_name,
        device=device,
    )

    synchronize_device(device)

    load_time = time.perf_counter() - load_started_at

    print(f"모델 로딩 시간: {load_time:.3f}초")

    # 첫 추론은 초기화 비용의 영향을 받을 수 있으므로
    # 워밍업 결과는 최종 평균에서 제외
    print("워밍업 추론 중...")

    warmup_result = model.transcribe(
        audio,
        language="ko",
        task="transcribe",
        fp16=device == "cuda",
        verbose=False,
    )

    synchronize_device(device)

    print(
        "워밍업 결과:",
        warmup_result.get("text", "").strip(),
    )

    inference_times = []
    recognized_texts = []

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

        print(f'{repeat_index + 1}회차: {inference_time:.3f}초 / "{recognized_text}"')

    average_inference_time = float(np.mean(inference_times))

    minimum_inference_time = float(np.min(inference_times))

    # 일반적으로 반복 결과는 같으므로 마지막 결과 사용
    final_text = recognized_texts[-1]

    cer = calculate_cer(
        REFERENCE_TEXT,
        final_text,
    )

    # 오디오 1초를 처리하는 데 걸리는 시간
    real_time_factor = average_inference_time / RECORD_SECONDS

    result_data = {
        "model": model_name,
        "load_time": load_time,
        "average_inference_time": average_inference_time,
        "minimum_inference_time": minimum_inference_time,
        "real_time_factor": real_time_factor,
        "cer": cer,
        "text": final_text,
    }

    release_model(model, device)

    return result_data


def print_summary(results: list[dict]) -> None:
    print("\n")
    print("=" * 100)
    print("Whisper 모델 성능 비교")
    print("=" * 100)

    header = (
        f"{'Model':<10}"
        f"{'Load(s)':>10}"
        f"{'Avg(s)':>10}"
        f"{'Min(s)':>10}"
        f"{'RTF':>10}"
        f"{'CER':>10}"
        f"  Result"
    )

    print(header)
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
    device = select_device()

    print(f"측정 장치: {device}")
    print(f"비교 모델: {MODEL_NAMES}")

    # 모든 모델이 정확히 같은 음성을 사용하도록 한 번만 녹음
    audio = record_audio()

    results = []

    for model_name in MODEL_NAMES:
        try:
            result = benchmark_model(
                model_name=model_name,
                audio=audio,
                device=device,
            )

            results.append(result)

        except Exception as error:
            print(f"{model_name} 모델 측정 실패: {type(error).__name__}: {error}")

    print_summary(results)


if __name__ == "__main__":
    main()
