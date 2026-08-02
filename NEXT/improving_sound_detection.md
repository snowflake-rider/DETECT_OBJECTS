# Improving mixed and noisy sound detection

## Recommendation

Keep Apple SoundAnalysis as the normal path. Before adding a separator or replacing the classifier, use **multiple analysis time scales, label-specific thresholds, and temporal aggregation**. The four challenge files show that the current misses are partly configuration problems, but not all of them.

Then benchmark one portable second opinion—MIT AST on CPU—against the same evaluation set. Add text-conditioned source separation only as an **offline, low-confidence fallback**, initially as an isolated AudioSep experiment rather than a runtime dependency.

```text
audio
  -> SoundAnalysis short-window request (animal/transient sounds)
  -> SoundAnalysis medium-window request (engines/continuous sounds)
  -> fuse scores over time
  -> confident result: emit event
  -> ambiguous result: optional offline separator experiment
```

## What the current samples reveal

I reran the existing challenge WAVs while preserving all five target scores instead of filtering at `0.5`. These numbers are the maximum confidence in each file; they are a small synthetic diagnostic, not an accuracy benchmark.

| Challenge | Current 3.0 s / 0.50 overlap | Better tested setting | Result |
|---|---:|---:|---|
| cat + dog overlap | dog `0.483` | 1.0 s / 0.50 | dog `0.950` |
| cat over engine | cat `0.989`, engine `0.981` | 1.5 s / 0.50 | cat `0.991`, engine `0.996`, accelerating `0.710` |
| quiet dog over race car | dog `0.020` | 0.5 s / 0.75 | dog `0.367` |
| race car with pink noise | race `0.115` | 0.75 s / 0.50 | race `0.326` |
| race car with pink noise | accelerating `0.128` | 2.0 s / 0.50 | accelerating `0.377` |

There is no single best window. Short windows recover brief barks; longer windows retain the pitch evolution and context of engines. Apple documents the same trade-off: smaller windows improve temporal precision, while larger windows can improve classification when a sound needs more context. Apple recommends one second or longer as a starting point, supports 0.5–15 seconds, and says overlap helps avoid splitting a sound across windows. Overlap above `0.5` costs more computation. Confidence values are independent, so thresholds should be selected per label rather than treated like probabilities that sum to one. Sources: [Apple `windowDuration`](https://developer.apple.com/documentation/soundanalysis/snclassifysoundrequest/windowduration), [Apple `overlapFactor`](https://developer.apple.com/documentation/soundanalysis/snclassifysoundrequest/overlapfactor), [WWDC21 built-in sound classification](https://developer.apple.com/videos/play/wwdc2021/10036/).

### First changes to evaluate

1. Run a short request around `0.75–1.0 s` with `0.5–0.75` overlap for `cat_meow` and `dog_bark`.
2. Run a second request around `1.5–2.0 s` with `0.5` overlap for engine labels.
3. Fuse adjacent windows into events. Use a higher threshold to start an event and a lower threshold to continue it; suppress isolated one-window spikes.
4. Tune separate thresholds on real positive clips, mixtures at several signal-to-noise ratios, and hard negatives. The challenge results suggest evaluating roughly `0.30–0.40` for the difficult dog/race labels, but they do **not** justify changing production thresholds without measuring false positives.
5. Keep the original waveform. Any enhanced or separated waveform should add evidence, not replace the original result.

## Would another classifier help?

Possibly, but published aggregate AudioSet scores do not prove better performance on quiet dog-versus-engine mixtures. Benchmark the exact target classes and mixtures.

| Candidate | Why consider it | Why not make it the default now? |
|---|---|---|
| **AST** | Straightforward Transformers/PyTorch integration; 16 kHz; AudioSet model available. The selected single checkpoint reports mAP `0.459`. | About 346 MB and much heavier than the OS classifier. Use CPU so it does not compete with YOLO for MPS. |
| **BEATs** | Accuracy-first AudioSet alternative; the official iter3+ single-model result reports mAP `0.486`. | Roughly 90M parameters, custom repository code/checkpoints, and more integration work. |
| **PANNs** | PyTorch, MIT-licensed code, mAP up to `0.439`; official models include frame-wise sound-event detection. | Older dependency stack and lower aggregate accuracy than AST/BEATs. |
| **YAMNet** | Small MobileNetV1 model with 521 AudioSet classes. | Adds TensorFlow to this PyTorch project and is primarily useful as a compact baseline. |
| **CLAP** | Open-vocabulary prompts such as “quiet Formula One engine accelerating.” | Embedding similarity is useful for retrieval/zero-shot ranking, but is not a calibrated independent event probability. It is better as an exploratory second opinion than the main detector. |

Primary sources: [AST documentation and checkpoint](https://huggingface.co/docs/transformers/model_doc/audio-spectrogram-transformer), [BEATs official repository](https://github.com/microsoft/unilm/tree/master/beats), [PANNs official repository](https://github.com/qiuqiangkong/audioset_tagging_cnn), [YAMNet official tutorial](https://www.tensorflow.org/hub/tutorials/yamnet), [LAION CLAP official repository](https://github.com/LAION-AI/CLAP). All of these AudioSet-derived classifiers cover relevant categories such as dog, cat, engine, and race car in the [official AudioSet ontology/dataset](https://research.google.com/audioset/dataset/index.html).

**Practical order:** AST first, BEATs only if AST materially improves recall but still misses important cases. Do not add several large classifiers simultaneously.

## Would denoising or source separation help?

### Generic or speech denoising: usually the wrong first step

Noise reduction can help when the interference is truly stationary noise, but a cat, bark, and engine are all meaningful non-speech sources. A speech enhancer can classify those targets as interference and remove or distort exactly what needs detection. DeepFilterNet is explicitly a speech-enhancement/noise-suppression system, while Demucs is trained to split music into vocals, drums, bass, and other; neither is designed to isolate cat/dog/vehicle events. Sources: [DeepFilterNet official repository](https://github.com/Rikorose/DeepFilterNet), [Demucs official repository](https://github.com/facebookresearch/demucs).

Simple preprocessing may still be safe to test: channel downmixing, sample-rate normalization, DC removal, and conservative level normalization. Avoid aggressive gates or band-pass filters unless evaluation shows they preserve every target class.

### Text-conditioned environmental separation: relevant, but expensive

AudioSep is aligned with this use case: query the same mixture with “cat meowing,” “dog barking,” and “race-car engine” to produce target waveforms. Its official evaluation reports SDR improvement of `7.739 dB` on AudioSet and `10.040 dB` on ESC-50. A separate DCASE-oriented study reported a `7.22` percentage-point F1 improvement when language-queried separation preceded sound-event detection, but that is task-specific evidence—not proof that it improves Apple SoundAnalysis on these clips. Sources: [AudioSep official repository](https://github.com/Audio-AGI/AudioSep), [AudioSep paper](https://arxiv.org/abs/2308.05037), [AudioSep-DP/TQ-SED paper](https://arxiv.org/abs/2409.13292).

The cost is substantial for this Mac-first application:

- The official AudioSep assets total `3.62 GB`: a `1.26 GB` separator checkpoint plus a `2.35 GB` CLAP checkpoint.
- Official inference selects CUDA when available and otherwise CPU; it documents no MPS or Core ML path.
- The published conda environment is Linux/CUDA-specific, so Apple Silicon installation requires dependency modernization and validation.
- Running several text queries multiplies separation cost.

Sources: [official AudioSep checkpoint files](https://huggingface.co/spaces/Audio-AGI/AudioSep/tree/main/checkpoint), [official inference instructions](https://github.com/Audio-AGI/AudioSep#inference), [official environment](https://github.com/Audio-AGI/AudioSep/blob/main/environment.yml). PyTorch supports Metal through MPS generally, but that does not guarantee that AudioSep's complete operator graph works there: [PyTorch MPS documentation](https://docs.pytorch.org/docs/stable/notes/mps.html).

CLAPSep supports positive and negative text/audio queries and reports stronger results than AudioSep on several research benchmarks. It is less suitable as a current product dependency: the model is non-causal, the official path is CUDA-oriented, the assets are large, and the public repository does not present a clear product-ready package/license. Source: [CLAPSep paper](https://arxiv.org/abs/2402.17455).

SAM-Audio is a newer future option, especially because this project already has video: it accepts text, time spans, or masked video prompts, with official examples including “a dog barking” and “car engine revving.” For now it is also a heavy research path: CUDA is recommended, checkpoints are gated, and it uses the SAM license. Source: [Meta SAM-Audio official repository](https://github.com/facebookresearch/sam-audio).

## Proposed experiment sequence

1. Build a small labeled evaluation set: clean sounds, the current synthetic mixtures, real video audio, hard negatives, and several signal-to-noise ratios.
2. Evaluate multi-scale SoundAnalysis plus per-label thresholds. Record event precision/recall, not just whether any window fires.
3. Add AST as an offline CPU comparison and test score-level fusion with SoundAnalysis.
4. Only if important low-volume targets remain missed, prototype AudioSep in an isolated environment on cropped ambiguous windows. Run it once per target query, classify both the original and separated signals, and measure whether recall improves without unacceptable false positives or latency.
5. Keep AudioSep out of the real-time video path unless the M5 benchmark demonstrates acceptable memory, latency, and coexistence with YOLO.

The main conclusion is: **better segmentation and event aggregation come first; a second classifier comes next; semantic source separation is a selective fallback, not preprocessing for every window.**
