# Audio source separation

Research date: 2026-08-02

## Current approach

Use SAM-Audio Small FP16 through MLX-Audio to isolate a sound described by a
text prompt. This is an optional, offline prototype rather than part of the
real-time detection path.

SAM-Audio does not discover every sound by itself and should only run for a
specific prompt and selected clip.

## Rules

- Run separation only on short, selected clips and keep it outside the real-time path.
- Benchmark audio processing while YOLO is running because both use shared Mac resources.
- Preserve the original audio alongside the target and residual outputs.

## Evaluation

1. Test short mixtures and real recordings with explicit prompts.
2. Measure separation quality, latency, memory, and video FPS.
3. Keep the prototype outside the real-time path unless resource measurements
   support tighter integration.

## Main references

- [SAM-Audio](https://github.com/facebookresearch/sam-audio)
- [MLX-Audio SAM-Audio support](https://github.com/Blaizzy/mlx-audio#sam-audio-source-separation)
