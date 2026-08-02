# Improve sound detection

## Goal

Detect quiet or overlapping animal and vehicle sounds more reliably.

## Plan

1. Keep Apple SoundAnalysis as the default detector.
2. Test two window sizes:
   - `0.75–1.0 s` for short sounds such as barks and meows.
   - `1.5–2.0 s` for continuous sounds such as engines.
3. Set a separate confidence threshold for each label and merge nearby detections into one event.
4. Measure precision and recall on clean audio, mixed audio, real recordings, and hard negatives.
5. If results are still weak, compare AST on CPU.
6. Use SAM-Audio only as an offline fallback for short, ambiguous clips.

## Avoid

- Do not run source separation on every clip.
- Do not replace the original audio with processed audio.
- Do not add several large classifiers at once.

## Order

**Tune SoundAnalysis first, test AST second, and use source separation last.**
