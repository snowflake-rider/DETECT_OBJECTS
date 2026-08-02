import sounddevice as sd
import soundfile as sf


SAMPLE_RATE = 16_000
CHANNELS = 1
DURATION_SECONDS = 5
OUTPUT_FILE = "test.wav"


def record_audio() -> None:
    print(f"{DURATION_SECONDS}초 동안 녹음합니다.")
    print("말씀하세요...")

    audio = sd.rec(
        int(DURATION_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
    )

    sd.wait()

    sf.write(
        OUTPUT_FILE,
        audio,
        SAMPLE_RATE,
    )

    print(f"녹음 완료: {OUTPUT_FILE}")


if __name__ == "__main__":
    record_audio()
