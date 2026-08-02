# Sound-event classifier research for Apple Silicon

Research date: 2026-08-02

Target environment: Apple M5 MacBook Air (10 CPU cores, 16 GB unified memory,
macOS 26.5.2), with YOLO-World already using PyTorch and preferably running on
MPS. The first target videos contain cat meows, dog barks, engines, and race
cars. The planned pipeline classifies overlapping audio windows while video
playback and vision inference continue.

## Recommendation

Use **Apple SoundAnalysis' built-in classifier as the default macOS backend**.
It is the best match for this Mac and the current label set:

- The OS classifier is hardware-accelerated, runs locally, supports independent
  confidence scores for simultaneous sounds, and returns a time range for every
  result window.
- This Mac exposes 303 built-in labels, including `cat_meow`, `dog_bark`,
  `engine`, `engine_accelerating_revving`, and `race_car`.
- It needs no downloaded weight artifact. Python can call it through
  `pyobjc-framework-SoundAnalysis`, and `import SoundAnalysis` already succeeds
  in this project's current environment.
- In the one-file exploratory measurement below, it was materially lighter and
  faster than AST. That is not an accuracy benchmark, but it confirms that the
  native path has ample scheduling headroom beside YOLO.

Keep **MIT AST on CPU as the portable fallback/reference implementation**. It
has a current Hugging Face integration, exact AudioSet coverage for all four
target labels, a permissive model license, and this machine processed the test
clip far faster than real time on CPU. CPU placement prevents AST from sharing
the PyTorch MPS device with YOLO.

If a smaller portable worker becomes more important than Hugging Face
convenience, evaluate **PANNs MobileNetV1** next. Its official checkpoint is only
23.6 MB and reports 0.389 AudioSet mAP, but the official integration is older
and more manual. Do not begin with BEATs or CLAP: they add size and integration
cost that the initial fixed AudioSet label set does not need.

This recommendation separates two questions:

| Goal | Choice |
|---|---|
| Best backend for this Mac | Apple SoundAnalysis built-in classifier |
| Best portable, straightforward PyTorch baseline | MIT AST on CPU |
| Best compact portable checkpoint to investigate | PANNs MobileNetV1 |
| Highest published single-model AudioSet mAP in this comparison | BEATs iter3+ |
| Best later option for arbitrary text labels | LAION CLAP (prefer over Microsoft CLAP here) |

## Evidence summary

The AudioSet-based fixed-label models all cover the required sounds. Google's
official AudioSet listing contains `Meow`, `Bark`, `Engine`, and
`Race car, auto racing`; the [YAMNet class map](https://github.com/tensorflow/models/blob/master/research/audioset/yamnet/yamnet_class_map.csv)
confirms those output labels directly. AudioSet is a multi-label dataset of
10-second clips, so mAP is the relevant published metric. Results below are
only compared where they use the AudioSet evaluation task; YAMNet uses 521
classes rather than 527, and Apple and CLAP do not publish a directly comparable
number for the checkpoint/API considered here.

| Candidate | Official evidence | Size | Window/input | Event and multi-label behavior | Repository-fit inference |
|---|---|---:|---|---|---|
| **Apple SoundAnalysis built-in** | 300+ categories; hardware-accelerated on-device; independent confidences; result time ranges | OS-managed; Apple does not publish parameters/artifact size | Configurable 0.5-15 s; default observed as 3 s; default overlap 0.5 | Native overlapping-window detection; simultaneous labels are explicitly supported | **Best Mac default.** No PyTorch weight allocation and no artifact download. Apple chooses the actual compute units, so total CPU/GPU contention still needs an end-to-end test. macOS-only. |
| **MIT AST AudioSet 0.4593** | 0.459 single-checkpoint mAP on 527 AudioSet classes | 86,594,063 parameters; 346,404,948-byte safetensors artifact | 16 kHz; 1,024 spectrogram frames (about 10.24 s), with shorter clips padded | Clip-level multi-label tagging; use overlapping windows for approximate timing. The original implementation applies sigmoid. | **Best portable baseline.** Existing PyTorch stack plus `transformers`; CPU placement leaves MPS to YOLO. Larger than needed for the first four labels. |
| **PANNs MobileNetV1** | 0.389 mAP on 527 AudioSet classes; official compact checkpoint | 23,639,473-byte checkpoint | 32 kHz default; trained on AudioSet's 10 s clips | Clip-level sigmoid outputs; slide windows for timing. Separate Cnn14 decision-level checkpoints provide framewise SED. | **Best compact portable candidate.** Likely lower memory pressure than AST based on artifact/architecture, but that is an inference and has not been benchmarked here. Official code targets an old dependency stack. |
| **BEATs iter3+ AudioSet** | 0.486 single-model mAP; 90M parameters | 90M parameters; official OneDrive checkpoint size not stated in the repo | 16 kHz; raw waveform plus padding mask; trained/evaluated on AudioSet clips | Fine-tuned checkpoint produces independent sigmoid probabilities; timing requires sliding windows | **Accuracy-first research option.** Manual repo integration and transformer cost offer little initial benefit over AST/native classification. |
| **LAION CLAP HTSAT** | Audio-text contrastive model; accepts arbitrary text labels; its underlying HTS-AT AudioSet encoder checkpoint reports 0.467 mAP, which is not a directly comparable CLAP tagging result | Hugging Face `clap-htsat-unfused` PyTorch artifact is 614,525,833 bytes | 48 kHz; 10 s maximum/default feature window; fused variants support variable length | Zero-shot label similarity, not a calibrated fixed multi-label event detector; default candidate-label scoring is relative across prompts | **Save for open vocabulary.** Useful for prompts such as “an F1 engine accelerating,” but heavier and less predictable for thresholded simultaneous events. |
| **Microsoft CLAP 2023** | Audio-text contrastive model evaluated across downstream tasks; open-vocabulary rather than a fixed AudioSet head | Official 2023 Zenodo checkpoint is 689,950,036 bytes | 44.1 kHz; 7 s configured duration | Zero-shot label similarity; not a calibrated independent event detector | **Not a Mac-first choice.** Official wrapper exposes CPU or CUDA, not MPS; heavier and less integrated here than LAION CLAP through Transformers. |
| **Google YAMNet** | 0.306 balanced mAP on 521 classes; 3.7M weights and 69.2M multiplies per frame | 3.7M weights | 16 kHz mono; 0.96 s frames every 0.48 s | Independent sigmoid score vector per frame, naturally useful for timing | **Smallest strong temporal baseline, but poor fit to the current stack.** Adds TensorFlow/TFLite beside PyTorch; official Keras code currently requires Keras 2 and is incompatible with Keras 3. |

### Metric caution

- AST's often-quoted 0.485 mAP is a six-model ensemble. The downloadable
  `MIT/ast-finetuned-audioset-10-10-0.4593` checkpoint is the 0.459
  single-model result.
- BEATs iter3+ reports 0.486 for a single model and 0.506 for an ensemble; the
  single-model value is the relevant comparison.
- PANNs' 0.439 result is Wavegram-Logmel-CNN14, not the compact MobileNetV1.
  MobileNetV1 is 0.389. The official compact alternatives include MobileNetV2
  at 20.8 MB/0.383, Cnn10 at 25.2 MB/0.380, and Cnn6 at 23.7 MB/0.343.
- YAMNet drops six AudioSet labels, so its 0.306 average covers 521 classes. It
  still contains every label needed by the initial videos.
- CLAP's repository mentions an HTS-AT audio encoder initialized from a 0.467
  mAP AudioSet checkpoint. That does not establish 0.467 mAP for zero-shot CLAP
  prompt classification and is not used to rank it here.

### Licensing summary

These are the licenses declared by each first-party distribution; this is an
inventory, not legal advice:

| Candidate | Declared license |
|---|---|
| Apple SoundAnalysis | OS framework with no separately distributed weights; use is governed by Apple's platform/SDK terms |
| MIT AST | BSD-3-Clause on the official repository and Hugging Face model card |
| PANNs | MIT source code; official Zenodo checkpoint artifacts are CC-BY-4.0 |
| Microsoft BEATs | MIT repository; the README does not declare a separate checkpoint license |
| LAION CLAP | Official repository code is CC0-1.0; the Hugging Face `clap-htsat-unfused` model card declares Apache-2.0 |
| Microsoft CLAP | MIT source code; official Zenodo 2023 weights record declares CC-BY-3.0-US; the Hugging Face `microsoft/msclap` card declares MS-PL |
| Google YAMNet | Apache-2.0 TensorFlow Models repository |

## Candidate details

### 1. Apple SoundAnalysis built-in classifier

**Source facts.** Apple's [SoundAnalysis documentation](https://developer.apple.com/documentation/SoundAnalysis)
and [WWDC21 session](https://developer.apple.com/videos/play/wwdc2021/10036/)
describe a built-in classifier with over 300 categories on all Apple platforms.
Computations are optimized for hardware acceleration and run locally. Each
overlapping analysis window returns labels, independent confidence scores, and a
time range. The classifier can identify several sounds at once; its scores do
not sum to one. Supported window durations range from 0.5 to 15 seconds, and
Apple recommends one second or longer as a starting point. The request's
[`overlapFactor`](https://developer.apple.com/documentation/soundanalysis/snclassifysoundrequest/overlapfactor)
defaults to 0.5.

The [PyObjC SoundAnalysis binding](https://pyobjc.readthedocs.io/en/latest/apinotes/SoundAnalysis.html)
exposes Apple's framework to Python as `import SoundAnalysis` on macOS 10.15+.

**Local verification.** Querying
`SNClassifySoundRequest(classifierIdentifier: .version1).knownClassifications`
on this Mac returned 303 labels. Relevant identifiers were:

```text
cat, cat_meow, cat_purr
dog, dog_bark, dog_bow_wow, dog_growl, dog_howl, dog_whimper
engine, engine_accelerating_revving, engine_idling, engine_knocking,
engine_starting
race_car, car_horn, car_passing_by, vehicle_skidding
```

**Project inference.** This is the strongest initial choice because it already
does windowing, temporal results, and independent multi-label scoring without a
second Python ML framework or a model artifact. It also avoids putting another
model in PyTorch's MPS allocator while YOLO is running. It does not preserve the
project's possible future Linux/Raspberry Pi portability, and Apple publishes
neither an AudioSet mAP nor the underlying model size. Treat AST as the portable
behavioral reference and keep the sound-classifier interface backend-neutral.

There is no weight file to place in `model_artifacts/`; the artifact is part of
macOS. Configuration should name the backend and window/threshold policy, not a
fake local path.

### 2. MIT Audio Spectrogram Transformer (AST)

**Source facts.** The [official AST repository](https://github.com/YuanGongND/ast)
uses 16 kHz audio and reports 0.459 mAP for its best downloadable weighted-
average single model. The 0.475 and 0.485 results are ensembles. The
[Hugging Face checkpoint](https://huggingface.co/MIT/ast-finetuned-audioset-10-10-0.4593)
contains 86,594,063 float32 parameters and a 346,404,948-byte safetensors file;
its model card is BSD-3-Clause. The original evaluation applies sigmoid to the
logits because AudioSet labels are not mutually exclusive.

The [Transformers audio pipeline](https://huggingface.co/docs/transformers/main_classes/pipelines)
defaults to softmax for multi-class audio models. Therefore, using the generic
pipeline with this AST checkpoint must explicitly set `function_to_apply="sigmoid"`
or apply `torch.sigmoid(logits)` directly. Otherwise simultaneous sounds are
incorrectly forced to compete.

**Project inference.** AST is still the cleanest cross-platform implementation:
one extra major dependency (`transformers`), a well-defined 527-label mapping,
and no TensorFlow runtime. Use CPU first. The local measurement below shows
ample throughput for a 2.5-second hop, and CPU placement leaves YOLO alone on
MPS. AST provides clip tags, not strong event boundaries, so use overlapping
windows and attach each result to the window's time range.

### 3. PANNs

**Source facts.** The [official PANNs repository](https://github.com/qiuqiangkong/audioset_tagging_cnn)
provides PyTorch models for 527-class AudioSet tagging and sound event detection.
Its default models operate at 32 kHz; an official 16 kHz Cnn14 checkpoint is
also available. Clipwise models apply sigmoid. Decision-level Cnn14 models
return both clipwise and framewise outputs.

The authors' [official Zenodo checkpoint record](https://zenodo.org/records/3987831)
contains the following relevant artifacts:

| Checkpoint | Bytes | AudioSet mAP | Role |
|---|---:|---:|---|
| MobileNetV1 | 23,639,473 | 0.389 | Recommended compact PANN candidate |
| MobileNetV2 | 20,834,417 | 0.383 | Smallest PANN candidate with similar quality |
| Cnn10 | 25,237,595 | 0.380 | Compact conventional CNN |
| Cnn6 | 23,698,321 | 0.343 | Compact but lower reported quality |
| Cnn14 | 327,428,481 | 0.431 | Full clip tagger |
| Cnn14 16 kHz | 358,668,570 | 0.438 | Full tagger matching the project's current 16 kHz audio path |
| Cnn14 DecisionLevelMax | 327,428,481 | 0.385 | Framewise sound event detection |

The source code is MIT-licensed; the Zenodo checkpoint record declares
CC-BY-4.0 for the artifacts. The official repo was developed on Python 3.7 and
lists old pinned dependencies, while the convenience `panns-inference` package
depends on `matplotlib`, `librosa`, and `torchlibrosa` and defaults to Cnn14.

**Project inference.** MobileNetV1 is the most interesting non-native efficiency
candidate: about one fifteenth of AST's artifact size with a 0.070 absolute mAP
gap. However, this repository would need to own a small modernized adapter for
preprocessing/checkpoint loading. That integration work should follow, not
precede, a native SoundAnalysis proof of concept. The compact checkpoint is
clipwise only; use sliding windows unless true framewise SED becomes a
requirement.

### 4. Microsoft BEATs

**Source facts.** The [official BEATs implementation](https://github.com/microsoft/unilm/tree/master/beats)
loads 16 kHz waveforms, creates 128-bin filterbanks, and its AudioSet-finetuned
head returns sigmoid probabilities. The [BEATs paper](https://proceedings.mlr.press/v202/chen23ag.html)
reports 90M parameters and 48.6% single-model mAP for iter3+ on AudioSet-2M;
50.6% is the ensemble result. The repository is MIT-licensed and publishes
fine-tuned checkpoints through OneDrive, but does not state a separate
checkpoint license or artifact byte size.

**Project inference.** BEATs offers the strongest published fixed-label accuracy
in this set, but it has no first-party Transformers packaging and uses custom
repository modules plus torchaudio feature extraction. Its 90M-parameter
transformer is not a sensible first companion to YOLO when Apple native and AST
already cover all required labels. Revisit only if evaluation clips show that
AST/native accuracy is inadequate.

### 5. LAION CLAP

**Source facts.** The [official LAION CLAP repository](https://github.com/LAION-AI/CLAP)
learns aligned audio and text representations and recommends its AudioSet
checkpoints for general audio under ten seconds. The
[Transformers CLAP documentation](https://huggingface.co/docs/transformers/model_doc/clap)
specifies 48 kHz input and a ten-second maximum feature window. The official
repository code is CC0-1.0; the Hugging Face
[`laion/clap-htsat-unfused`](https://huggingface.co/laion/clap-htsat-unfused)
checkpoint card declares Apache-2.0 and its PyTorch artifact is 614,525,833
bytes.

**Project inference.** CLAP's value is open-vocabulary search: candidate prompts
can distinguish “engine,” “race car,” and “an F1 engine accelerating” without
retraining a 527-way head. Its default zero-shot pipeline normalizes scores
across candidate labels, so it is not a drop-in replacement for calibrated,
independent multi-label probabilities. Prompt wording and thresholds would need
validation. Cache text embeddings if this is added later.

### 6. Microsoft CLAP

**Source facts.** Microsoft's [official CLAP repository](https://github.com/microsoft/CLAP)
also implements contrastive audio-language learning. The official 2023
[configuration](https://github.com/microsoft/CLAP/blob/main/msclap/configs/config_2023.yml)
uses 44.1 kHz audio and a seven-second duration. Its
[Zenodo record](https://zenodo.org/records/8378278) lists the 2023 checkpoint at
689,950,036 bytes. The wrapper's public option is `use_cuda`; its source moves
models to CUDA when requested and otherwise leaves them on CPU, with no MPS
path. The source repository is MIT, the Zenodo record declares CC-BY-3.0-US,
and the separate [Hugging Face model card](https://huggingface.co/microsoft/msclap)
declares MS-PL.

**Project inference.** This option has the same open-vocabulary strengths and
calibration drawbacks as LAION CLAP, with a less direct Mac path. It is not a
good first model for four known AudioSet concepts. If CLAP becomes necessary,
LAION's Transformers-supported checkpoint is the more natural experiment for
this repository, subject to its own MPS validation.

### 7. Google YAMNet

**Source facts.** The [official YAMNet repository](https://github.com/tensorflow/models/tree/master/research/audioset/yamnet)
uses a MobileNetV1 depthwise-separable CNN. It consumes 16 kHz mono audio and
emits independent sigmoid scores for 0.96-second frames at a 0.48-second hop.
Google reports 3.7M weights, 69.2M multiplies per frame, and 0.306 balanced mAP
over its 521 AudioSet classes. The repository is Apache-2.0. The official README
also warns that the Keras implementation relies on Keras 2 and is incompatible
with Keras 3 (the default since TensorFlow 2.16).

**Project inference.** YAMNet is attractive when low-latency temporal output is
more important than average tagging quality. For this PyTorch project, adding a
second full framework is poor leverage; using the official TFLite artifact
would reduce runtime scope but introduce a separate adapter and still provide
lower published mAP than PANNs MobileNetV1. It is a fallback for a very small
edge worker, not the first Mac implementation.

## One-machine exploratory measurement

These numbers are **local engineering measurements, not published benchmarks**.
They use one clean Google sample
[`miaow_16k.wav`](https://storage.googleapis.com/audioset/miaow_16k.wav)
(6.73 seconds), so they say
nothing reliable about class-level accuracy, mixed sounds, noisy video, or
confidence calibration. They only test basic correctness and approximate
resource/latency scale on the target machine.

| Backend | Measurement on this M5 MacBook Air |
|---|---|
| Apple SoundAnalysis | Ten-run median total setup + file analysis: **0.0522 s**; median `analyze()` portion: **0.0199 s**; first total: **0.120 s**; three result windows; final top results `cat_meow` 0.9726 and `cat` 0.9432; exploratory process max RSS about **99.6 MB** |
| AST CPU | Five-run inference around **0.235 s**; cached model load **0.201 s**; preprocessing median **0.0047 s**; initial network download + load **13.286 s**; top results `Cat` 0.8176 and `Meow` 0.5429; exploratory process max RSS about **428.9 MB** |
| AST MPS | Five-run inference around **0.117 s** on the same prepared input |

Do not compare the Apple and AST confidence numbers directly: the models have
different taxonomies, training, calibration, and windowing. Both correctly
surfaced the relevant cat/meow concepts. AST CPU was already much faster than
the proposed 2.5-second hop, so moving it to MPS is unnecessary unless an
end-to-end workload later proves otherwise.

## Coexistence with YOLO

Recommended initial scheduling:

```text
video
├── frames → YOLO-World → PyTorch MPS
└── audio  → SoundAnalysis → OS-managed hardware execution
             └── portable fallback: AST → PyTorch CPU
```

This placement is a project inference from the model evidence and the local
measurement:

1. Keep the continuously running vision path on MPS.
2. Run sound analysis only when an overlapping audio window is ready.
3. Do not run AST on MPS initially; its measured CPU latency is already far
   below the hop duration.
4. Keep one loaded classifier instance instead of loading per window.
5. Bound the audio queue and discard stale work rather than pausing playback.
6. Benchmark the combined process, because Apple's native runtime may still
   choose GPU/Neural Engine resources and unified memory is shared.

PyTorch's [MPS documentation](https://docs.pytorch.org/docs/stable/notes/mps.html)
confirms that moving a model to `mps` uses Metal Performance Shaders. The
backend remains described as beta by Apple, and PyTorch provides
`PYTORCH_ENABLE_MPS_FALLBACK=1` for unsupported operations. This repository
already contains a YOLO MPS-to-CPU fallback, another reason to avoid assuming
that every audio model is automatically best on MPS.

### Acceleration and Core ML path

| Candidate | Verified path | What remains an inference or experiment |
|---|---|---|
| Apple SoundAnalysis | First-party native framework; Apple says it is optimized for on-device hardware acceleration | The framework does not expose placement control, so measure coexistence with YOLO rather than assuming it only uses the Neural Engine |
| AST | Official PyTorch/Transformers implementation; CPU and MPS both ran in the local probe | Core ML Tools can convert PyTorch generally, but there is no first-party AST recipe; conversion and output parity would need proof |
| PANNs MobileNetV1 | Official PyTorch checkpoint and source | MPS and Core ML were not verified. A convolutional MobileNet is a plausible conversion candidate, but that is architectural inference, not a supported-path claim |
| BEATs | Official PyTorch source | MPS/Core ML support is unverified; torchaudio's Kaldi filterbank preprocessing also needs a deliberate device boundary |
| LAION CLAP | Official PyTorch package and Transformers support | MPS/Core ML support is unverified; cache text embeddings before any performance comparison |
| Microsoft CLAP | Official PyTorch wrapper supports CPU or CUDA | No official MPS/Core ML path; changing device handling would be project-owned work |
| YAMNet | Official TensorFlow SavedModel and TFLite paths | It is not a PyTorch MPS model. Core ML Tools supports TensorFlow generally, but no first-party YAMNet conversion recipe was found |

Core ML conversion is not the first step. Apple's
[Core ML Tools documentation](https://apple.github.io/coremltools/docs-guides/source/load-and-convert-model.html)
supports converting traced/exported PyTorch models, and Core ML can use CPU,
GPU, and Neural Engine compute units. However, conversion support and speed are
model-specific and must be validated; no first-party recipe was found for AST,
PANNs, BEATs, CLAP, or YAMNet. The built-in SoundAnalysis classifier already
provides the native route without conversion.

## Configuration shape

For the native default, keep model selection in `config/models.toml` but omit a
weight path:

```toml
[audio.sound_classifier]
backend = "apple_soundanalysis"
classifier_version = 1
window_seconds = 3.0
overlap = 0.5
top_k = 5

[audio.sound_classifier.thresholds]
cat_meow = 0.5
dog_bark = 0.5
engine = 0.5
engine_accelerating_revving = 0.5
race_car = 0.5
```

Thresholds above are placeholders, not researched optimums. Apple explicitly
recommends per-sound thresholds because scores are independent and window
duration changes calibration. Tune them on representative project videos.

If portable execution is selected, use a backend-specific section with a real
artifact identifier/path:

```toml
[audio.sound_classifier]
backend = "ast_audioset"
model_id = "MIT/ast-finetuned-audioset-10-10-0.4593"
artifact_dir = "../model_artifacts/audio/ast-audioset"
sample_rate = 16000
window_seconds = 5.0
hop_seconds = 2.5
device = "cpu"
activation = "sigmoid"
```

The 5-second AST window is a pipeline choice, not the checkpoint's native
training duration; the feature extractor pads it to the fixed spectrogram
length. Compare 3, 5, and 10-second windows during evaluation.

## Decision gates before implementation

1. Confirm whether macOS-only execution is acceptable for the first milestone.
   If yes, implement SoundAnalysis first. If the first milestone must run on
   Linux/Raspberry Pi, implement AST CPU first.
2. Build a small evaluation set containing clean and mixed examples of meow,
   bark, general engine, accelerating engine, and race car, plus hard negatives.
3. Measure per-label precision/recall, missed-event rate, latency, process RSS,
   and video frame rate while YOLO is active. A single clean meow clip is not
   enough to choose thresholds or claim accuracy.
4. Only evaluate PANNs MobileNetV1 if native portability or memory becomes a
   real constraint; evaluate BEATs only if accuracy is inadequate; evaluate
   CLAP only if arbitrary labels become a requirement.

## Primary sources

- Apple: [SoundAnalysis framework](https://developer.apple.com/documentation/SoundAnalysis),
  [WWDC21 built-in classifier session](https://developer.apple.com/videos/play/wwdc2021/10036/),
  [overlap factor](https://developer.apple.com/documentation/soundanalysis/snclassifysoundrequest/overlapfactor),
  [Core ML compute units](https://apple.github.io/coremltools/docs-guides/source/new-conversion-options.html)
- PyObjC: [SoundAnalysis API notes](https://pyobjc.readthedocs.io/en/latest/apinotes/SoundAnalysis.html)
- AudioSet: [dataset and label coverage](https://research.google.com/audioset/dataset/index.html),
  [dataset/ontology licenses](https://research.google.com/audioset/download.html)
- AST: [official repository](https://github.com/YuanGongND/ast),
  [checkpoint/model card](https://huggingface.co/MIT/ast-finetuned-audioset-10-10-0.4593),
  [Transformers AST documentation](https://huggingface.co/docs/transformers/model_doc/audio-spectrogram-transformer)
- PANNs: [official repository](https://github.com/qiuqiangkong/audioset_tagging_cnn),
  [official checkpoint record](https://zenodo.org/records/3987831),
  [paper](https://arxiv.org/abs/1912.10211)
- BEATs: [official repository](https://github.com/microsoft/unilm/tree/master/beats),
  [paper](https://proceedings.mlr.press/v202/chen23ag.html)
- CLAP: [official repository](https://github.com/LAION-AI/CLAP),
  [Transformers documentation](https://huggingface.co/docs/transformers/model_doc/clap),
  [Hugging Face checkpoint](https://huggingface.co/laion/clap-htsat-unfused)
- Microsoft CLAP: [official repository](https://github.com/microsoft/CLAP),
  [2023 configuration](https://github.com/microsoft/CLAP/blob/main/msclap/configs/config_2023.yml),
  [official checkpoint record](https://zenodo.org/records/8378278),
  [Hugging Face model card](https://huggingface.co/microsoft/msclap)
- YAMNet: [official repository and model facts](https://github.com/tensorflow/models/tree/master/research/audioset/yamnet),
  [official TensorFlow Hub tutorial](https://www.tensorflow.org/hub/tutorials/yamnet)
- PyTorch: [MPS backend](https://docs.pytorch.org/docs/stable/notes/mps.html),
  [MPS environment variables](https://docs.pytorch.org/docs/stable/mps_environment_variables.html)
