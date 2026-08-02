# Audio detection and separation

Research date: 2026-08-02

## Current approach

Use two models for two different jobs:

| Job | Model | Use |
|---|---|---|
| Detect sounds | Apple SoundAnalysis | Default, always-on classifier |
| Separate one sound | SAM-Audio Small FP16 through MLX-Audio | Optional fallback for ambiguous clips |

SoundAnalysis is native, lightweight, and already recognizes the project's cat,
dog, engine, and race-car labels. SAM-Audio can isolate a sound described by a
text prompt, but it is much heavier and does not discover every sound by itself.

```text
audio -> SoundAnalysis -> confident result
                       -> ambiguous short clip -> SAM-Audio -> recheck result
```

## Rules

- Treat classifier scores as independent; do not apply softmax.
- Use overlapping windows and a separate threshold for each label.
- Keep top results visible even when they are below the event threshold.
- Preserve and classify the original audio when using separated audio.
- Run separation only on short, selected clips and keep it outside the real-time path.
- Benchmark audio processing while YOLO is running because both use shared Mac resources.

## Portable fallback

If macOS-only SoundAnalysis is no longer enough, evaluate EfficientAT on CPU
first. AST is a reasonable larger reference model. Consider BEATs only when
accuracy is inadequate and CLAP only when open-vocabulary labels are required.
Do not add several large classifiers at once.

## Evaluation

1. Test clean sounds, mixtures, real recordings, and hard negatives.
2. Tune window sizes and per-label thresholds.
3. Measure precision, recall, latency, memory, and video FPS.
4. Keep SAM-Audio only if it recovers missed sounds without excessive false
   positives or slowdown.

Sample provenance, licenses, expected labels, and challenge-mixture notes are
maintained beside the fixtures in [`samples/audio/README.md`](../../samples/audio/README.md).

## Main references

- [Apple SoundAnalysis](https://developer.apple.com/documentation/soundanalysis/)
- [EfficientAT](https://github.com/fschmid56/EfficientAT)
- [AST](https://github.com/YuanGongND/ast)
- [SAM-Audio](https://github.com/facebookresearch/sam-audio)
- [MLX-Audio SAM-Audio support](https://github.com/Blaizzy/mlx-audio#sam-audio-source-separation)
- [AudioSet](https://research.google.com/audioset/dataset/index.html)
