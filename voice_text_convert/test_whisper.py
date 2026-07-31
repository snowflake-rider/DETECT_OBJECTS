import numpy as np
import sounddevice as sd
import whisper


SAMPLE_RATE = 16_000
CHANNELS = 1
RECORD_SECONDS = 5


def record_audio() -> np.ndarray:
    print(f"{RECORD_SECONDS}초 동안 녹음합니다.")
    print("말씀하세요.")

    audio = sd.rec(
        int(RECORD_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype=np.float32,
    )

    sd.wait()

    print("녹음 완료")

    # shape: (샘플 수, 1) → (샘플 수,)
    return audio.squeeze()


def main() -> None:
    print("Whisper 모델을 불러옵니다.")
    model = whisper.load_model("base")

    audio = record_audio()

    print("음성을 인식합니다.")

    result = model.transcribe(
        audio,
        language="ko",
        task="transcribe",
        fp16=False,
    )

    text = result["text"].strip()

    print("========== 인식 결과 ==========")
    print(text)
    print(result)

if __name__ == "__main__":
    main()