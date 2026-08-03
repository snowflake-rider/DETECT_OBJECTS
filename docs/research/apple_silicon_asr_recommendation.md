# Apple-Silicon ASR recommendation for ODIA

Research date: 2026-08-03. Scope: short Korean voice commands on the project's 16 GB Apple-Silicon Mac while object detection may be running at the same time.

## Recommendation

There is no public Korean-command benchmark that proves one replacement universally beats Whisper. The best practical choices are:

1. **First non-Whisper candidate: Cohere Transcribe through FluidAudio/Core ML.** It explicitly supports Korean, has stronger general accuracy evidence than Whisper large-v3, and its Core ML port has an ANE-resident decoder. This is the most promising accuracy-first experiment that need not put the whole ASR workload on the GPU used by YOLO.
2. **First Python-friendly candidate: Qwen3-ASR-1.7B-8bit through MLX-Audio.** It has the strongest published multilingual evidence among the easy MLX options and supports Korean plus prompt/context biasing. It uses MLX's CPU/GPU backends, not the Neural Engine, so simultaneous YOLO MPS inference can create GPU and unified-memory contention.
3. **Speed/memory candidate: SenseVoiceSmall INT8 through FluidAudio/Core ML.** It is only about 225 MB in the FluidAudio INT8 export, is non-autoregressive, explicitly supports Korean, and places its encoder on the ANE. Its Korean accuracy relative to Whisper is unproven.
4. **Lowest-risk baseline: WhisperKit with compressed large-v3/turbo.** It remains Whisper, but fixes the current runtime problem by using Core ML and can execute on the ANE/GPU instead of forcing PyTorch CPU inference.

Apple `SpeechTranscriber` should also be tested because it is native, low-latency, system-managed, and entirely on-device. It is not yet the primary recommendation because Apple publishes neither Korean accuracy nor model size/compute placement, and Korean support must be queried on the actual machine at runtime.

## What “using all of Apple Silicon” actually means

Apple Silicon does not automatically spread every model evenly over CPU, GPU, and Neural Engine. The runtime and converted graph determine placement:

| Runtime | Compute it can use | Neural Engine? | ODIA consequence |
| --- | --- | --- | --- |
| Current `openai-whisper` PyTorch code | CPU, because ODIA explicitly loads with `device="cpu"` | No | All Whisper variants consume CPU; larger models merely consume more of it. |
| MLX / MLX-Audio | CPU and Metal GPU; arrays share unified memory | **No** | Good Python integration, but GPU ASR can compete with YOLO MPS. MLX officially lists CPU and GPU as its supported devices ([MLX repository](https://github.com/ml-explore/mlx)); shared memory removes copies but device choice is still explicit ([MLX unified-memory guide](https://ml-explore.github.io/mlx/build/html/usage/unified_memory.html)). |
| Core ML / FluidAudio / WhisperKit | CPU, GPU, and ANE, subject to graph/operator compatibility | **Yes** | Core ML can be allowed to select all units, or constrained to CPU+ANE to preserve GPU headroom. Apple documents these choices in [`MLComputeUnits`](https://developer.apple.com/documentation/coreml/mlcomputeunits). |
| Apple Speech framework | Opaque system-managed execution | Undocumented | Apple says it is fully on-device, but does not publish its compute-unit split. Do not assume it evenly uses CPU/GPU/ANE. |

Unified memory makes data accessible to multiple processors; it does not itself schedule operations across them.

## Candidate comparison

| Candidate | Korean support | Accuracy evidence versus Whisper | Latency / streaming | Download / memory evidence | Actual Apple execution |
| --- | --- | --- | --- | --- | --- |
| **Cohere Transcribe 2B + FluidAudio** | Yes; Korean is one of 14 official languages ([Cohere model overview](https://cohere.com/blog/transcribe), [Cohere docs](https://docs.cohere.com/docs/transcribe)) | Cohere reports mean WER 5.42 versus Whisper large-v3 7.44 and Qwen3-ASR-1.7B 5.76 on the English-oriented Open ASR Leaderboard suite. This is strong general evidence, **not Korean-specific proof**. | FluidAudio offers sliding-window, near-real-time transcription; individual calls are capped at 35 seconds, which is ample for ODIA commands. It is not a true cache-aware streaming model. | FluidAudio documents an INT8 encoder of about 1.8 GB plus a static FP32 decoder ([FluidAudio model guide](https://github.com/FluidInference/FluidAudio/blob/main/Documentation/Models.md#sliding-window-transcription-near-real-time)). Runtime peak for the complete Cohere pipeline is not published there. | Core ML. FluidAudio says the v2 static decoder remains ANE-resident and is about 1.6x faster than its previous dynamic decoder. Profile the encoder placement rather than assuming the full graph stays on ANE. |
| **Qwen3-ASR-1.7B-8bit + MLX-Audio** | Yes; Qwen lists `ko` among 30 languages and supports offline/streaming model modes ([official model card](https://huggingface.co/Qwen/Qwen3-ASR-0.6B)) | Qwen's aggregate multilingual evaluation includes Korean: 1.7B beats Whisper large-v3 on CommonVoice (9.18 vs 10.77), MLC-SLM (12.74 vs 15.68), and core FLEURS (4.90 vs 5.27). These are aggregate scores, not Korean-only WER. The 0.6B version is worse than Whisper on these aggregates ([evaluation table](https://huggingface.co/Qwen/Qwen3-ASR-0.6B#evaluation)). | Qwen's official streaming implementation currently requires its vLLM backend; its published streaming results lose some accuracy. MLX-Audio verifies ordinary Qwen3-ASR generation, but does not publish Apple-specific Korean latency or true Qwen streaming results. For ODIA, use VAD/end-of-command capture followed by fast offline generation first. | The MLX 1.7B 8-bit checkpoint is about 2.46 GB; the 0.6B 8-bit checkpoint is about 1.01 GB ([1.7B MLX card](https://huggingface.co/mlx-community/Qwen3-ASR-1.7B-8bit), [0.6B MLX card](https://huggingface.co/mlx-community/Qwen3-ASR-0.6B-8bit)). Live memory will exceed checkpoint size because of activations/cache. | MLX Metal GPU by default when configured for GPU; **no ANE**. This may contend directly with YOLO's MPS workload. |
| **Qwen3-ASR-0.6B-8bit + MLX-Audio** | Yes | Better than Whisper base is plausible, but Qwen's own aggregate table does not show it beating Whisper large-v3. It is an efficiency option, not the evidence-backed accuracy winner. | Same caveat as 1.7B. Short outputs keep autoregressive decode small. | About 1.01 GB checkpoint. A 4-bit conversion is about 708 MB of weights, but quantization should be validated against Korean command accuracy ([MLX 4-bit metadata](https://huggingface.co/mlx-community/Qwen3-ASR-0.6B-4bit/blob/main/model.safetensors.index.json)). | MLX GPU/CPU only. |
| **SenseVoiceSmall INT8 + FluidAudio** | Yes; the upstream project explicitly lists Korean ([SenseVoice repository](https://github.com/QwenAudio/SenseVoice)). | No published Korean comparison against Whisper. FluidAudio reproduces upstream English/Chinese accuracy after conversion (LibriSpeech WER 3.22%, AISHELL CER 3.09%), which validates conversion fidelity but not Korean quality. | Non-autoregressive: all tokens are produced in one forward pass, attractive for short commands. FluidAudio reports 299x median real-time on LibriSpeech on an M5 Pro; this is not an M5 Air or Korean measurement. | FluidAudio reports 225 MB and 0.32 GB peak RAM for INT8; FP16 is 447 MB and 0.54 GB peak ([FluidAudio SenseVoice benchmarks](https://github.com/FluidInference/FluidAudio/blob/main/Documentation/Benchmarks.md#sensevoice)). | FP32 front end on CPU, INT8/FP16 encoder+CTC on ANE, host greedy decode. This is the clearest low-GPU-contention design. |
| **WhisperKit compressed large-v3/turbo** | Yes; Whisper multilingual | Same Whisper family, so this is an execution upgrade rather than a new-model accuracy claim. | Microphone streaming and output streaming are supported. Argmax recommends compressed `large-v3-v20240930_626MB` for multilingual accuracy and the turbo variant on macOS for speed/accuracy ([WhisperKit README](https://github.com/argmaxinc/argmax-oss-swift#model-selection)). Argmax reports large-v3 turbo as fast as 72x real-time on an M2 Ultra with GPU+ANE, but that does not predict M5 Air performance ([WhisperKit benchmark note](https://github.com/argmaxinc/argmax-oss-swift/discussions/243)). | Compressed large-v3 package: approximately 627 MB; uncompressed turbo Core ML package: approximately 1.64 GB ([model repository](https://huggingface.co/argmaxinc/whisperkit-coreml/tree/main/openai_whisper-large-v3-v20240930_626MB)). | Core ML, with configurations that can use ANE and GPU. Prefer CPU+ANE initially if YOLO is on GPU, then benchmark `all`. |
| **Apple SpeechTranscriber** | Must be queried at runtime; Apple does not maintain a static public locale table | Apple calls its new model faster and more flexible than the older on-device recognizer and designed for distant, long-form, and live audio, but publishes no WER and no comparison with Whisper. | True live transcription with fast volatile results followed by improved final results. Entirely on-device. | Model assets are system-downloaded, shared, auto-updated, and live outside the app's storage/runtime-memory accounting ([WWDC25 SpeechAnalyzer session](https://developer.apple.com/videos/play/wwdc2025/277/), [AssetInventory docs](https://developer.apple.com/documentation/speech/assetinventory)). Physical model size is undisclosed. | System opaque; no documented CPU/GPU/ANE split. |

## Why Qwen3-ASR-1.7B, not Qwen2-Audio

Qwen3-ASR is a dedicated ASR model with explicit Korean support and a maintained MLX-Audio port. Qwen2-Audio is a much larger, general audio-language model rather than a low-latency ASR specialist. It adds memory and decoder overhead without better Korean evidence for this use case. MLX-Audio explicitly supports Qwen3-ASR 0.6B/1.7B and their quantized checkpoints ([MLX-Audio supported models and example](https://github.com/Blaizzy/mlx-audio#qwen3-asr--forcedaligner)).

Qwen3-ASR also supports free-form context/hotwords in its current Transformers-native interface ([official prompt example](https://huggingface.co/Qwen/Qwen3-ASR-0.6B-hf#context--hotwords)). That is particularly useful for ODIA: provide the known Korean command verbs and object names as context. Confirm that the selected MLX-Audio version passes the equivalent `system_prompt`/prompt through before relying on it.

## Apple SpeechTranscriber availability check

Apple's supported locales are device-, OS-, and asset-dependent. The documented method is `SpeechTranscriber.supportedLocale(equivalentTo:)` or `supportedLocales`, followed by an `AssetInventory` download request ([SpeechTranscriber docs](https://developer.apple.com/documentation/speech/speechtranscriber), [WWDC sample code](https://developer.apple.com/videos/play/wwdc2025/277/?time=730)).

A `swift -e` probe on this Mac (macOS 26.5.2) returned `SpeechTranscriber.isAvailable == true` but an empty `supportedLocales` list in the managed shell. That is inconclusive: repeat the check in a normal signed macOS app/process and specifically ask for `ko-KR`:

```swift
import Foundation
import Speech

let requested = Locale(identifier: "ko-KR")
if let supported = await SpeechTranscriber.supportedLocale(equivalentTo: requested) {
    print("Supported as \(supported.identifier)")
} else {
    print("Korean SpeechTranscriber model unavailable on this Mac/OS")
}
```

Do not select SpeechTranscriber for Korean until this returns a locale and the asset installs successfully.

## ODIA benchmark gate

Before changing the default, record a small in-domain set: at least 20 speakers/conditions if practical, the actual Korean verbs and object vocabulary, quiet and room-noise variants, and deliberate confusable object names. Measure:

- exact-command accuracy after the same normalization/intent parser;
- Korean character error rate as a diagnostic, not the sole product metric;
- capture-end to final-text p50/p95 latency;
- false activations and hallucinations during silence/noise;
- process and total system memory;
- YOLO FPS/latency while ASR runs concurrently.

Test this initial matrix:

1. Cohere Transcribe Core ML, explicit Korean prompt;
2. Qwen3-ASR-1.7B-8bit MLX, forced Korean plus command/object context;
3. SenseVoiceSmall INT8 Core ML;
4. WhisperKit compressed large-v3/turbo as the optimized Whisper baseline;
5. Apple SpeechTranscriber only if the runtime `ko-KR` check succeeds.

For the 16 GB Mac running YOLO, accuracy alone is not sufficient. If Qwen improves recognition but degrades detector latency because both models occupy the GPU, the Core ML CPU+ANE candidates are the better system-level choice.
