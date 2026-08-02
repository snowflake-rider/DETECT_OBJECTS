# Apple Silicon support for environmental sound separation

Research date: 2026-08-02

## Conclusion

For this project's M5 MacBook Air with 16 GB unified memory, the best currently documented Apple-Silicon option is **SAM-Audio Small FP16 through MLX-Audio**:

- Model: [`mlx-community/sam-audio-small-fp16`](https://huggingface.co/mlx-community/sam-audio-small-fp16)
- Runtime: [`Blaizzy/mlx-audio`](https://github.com/Blaizzy/mlx-audio#sam-audio-source-separation)
- Purpose: prompt-conditioned, general audio separation; prompts can describe environmental events such as `cat meowing`, `dog barking`, or `race car engine`.
- Output: an isolated target waveform and a residual/background waveform.
- Hardware path: MLX on the Apple Silicon GPU and unified memory. This is **not** Core ML and does not claim to use the Neural Engine.
- Checkpoint: about 1.20 GB (FP16, approximately 0.6B parameters). The runtime also needs memory for activations and audio buffers, so checkpoint size is not peak memory.

Meta's upstream [SAM-Audio repository](https://github.com/facebookresearch/sam-audio) confirms that the model handles general SFX, speech, music, and instruments using text, visual, or temporal prompts. Meta's own inference instructions recommend CUDA; Apple Silicon support comes from the community MLX port, not from the upstream Meta implementation.

Keep Apple SoundAnalysis as the always-on classifier. Run SAM-Audio only on selected ambiguous segments initially, because MLX and YOLO's PyTorch MPS backend both use the Apple GPU and unified memory.

## Support matrix

| Model/runtime | Environmental/text-conditioned? | Verified Apple path | Assessment |
|---|---|---|---|
| SAM-Audio via MLX-Audio | Yes; general sound, text prompt; upstream also supports visual/time prompts | Native MLX GPU on Apple Silicon | **Best match; prototype Small FP16** |
| SAM-Audio upstream | Yes | CUDA recommended; no upstream MPS/Core ML/MLX instructions | Do not use upstream runtime on this Mac |
| AudioSep | Yes; open-domain text query | Official code selects CUDA or CPU | Can execute on Apple CPU, but is not Apple-accelerated |
| CLAPSep | Yes; text/audio query-conditioned extraction | Official source has CUDA or CPU modes; no MPS/Core ML/MLX path | Research integration; CPU-only on Mac from documented paths |
| sherpa-onnx Spleeter/UVR | No; fixed music stems | ONNX Runtime CPU supports macOS arm64 | Fast and deployable, but wrong task |
| Demucs/MLX music ports | No; fixed music stems | MLX ports exist | Wrong task for cat/dog/engine extraction |
| DeepFilterNet/MossFormer2 MLX | No; speech enhancement | MLX-Audio supports them | May remove the environmental event as noise |
| Apple SoundAnalysis | Classification only | Native Apple framework | Detects labels; does not produce separated waveforms |

## What each Apple label means

### Native MLX GPU: yes

[MLX](https://github.com/ml-explore/mlx) is Apple's machine-learning array framework for Apple Silicon. Its official documentation says MLX operations can run on CPU or GPU and use Apple Silicon's shared unified memory. [MLX-Audio](https://github.com/Blaizzy/mlx-audio) explicitly lists SAM-Audio as text-guided source separation and documents target/residual output, long-file chunking, streaming, Metal cache management, and M-series performance modes.

The Python MLX-Audio project requires Apple Silicon and MLX. A separate [`mlx-audio-swift`](https://github.com/Blaizzy/mlx-audio-swift) project lists SAM-Audio and targets macOS 14+/iOS 17+, but the current Python project is the lower-friction match for this Python repository.

### PyTorch MPS: no verified implementation

None of the official AudioSep, CLAPSep, or Meta SAM-Audio instructions provides an MPS path. AudioSep's [official inference example](https://github.com/Audio-AGI/AudioSep#inference) explicitly chooses CUDA when available and CPU otherwise. CLAPSep's [official repository](https://github.com/Aisaka0v0/CLAPSep) exposes CUDA or CPU execution, with no documented MPS device.

Changing `cuda` to `mps` is not evidence of model compatibility: every operator and dependency would need to work on MPS and the result would need correctness and performance validation.

### Core ML / Neural Engine: no verified general separator

No maintained, documented Core ML conversion or public `.mlpackage` was found for AudioSep, CLAPSep, or SAM-Audio. Core ML Tools can generally convert supported PyTorch graphs, and Core ML can let the OS select the CPU, GPU, or Neural Engine, but that does not establish that these dynamic, multi-component generative separators convert successfully. See Apple's [Core ML Tools overview](https://apple.github.io/coremltools/docs-guides/source/overview-coremltools.html) and [`MLComputeUnits`](https://developer.apple.com/documentation/coreml/mlcomputeunits).

Apple [SoundAnalysis](https://developer.apple.com/documentation/soundanalysis/) is useful for classifying sound events but returns labels/confidences and time ranges, not isolated audio stems.

### ONNX on macOS ARM64: available, but only for narrower models

[`sherpa-onnx`](https://github.com/k2-fsa/sherpa-onnx) explicitly supports macOS arm64 and source-separation inference. Its published [source-separation models](https://k2-fsa.github.io/sherpa/onnx/source-separation/models.html), however, are fixed music-oriented Spleeter/UVR models rather than arbitrary text-conditioned environmental separation. They are useful for vocals/accompaniment, not for extracting a dog from an engine mixture.

## Model-specific notes

### SAM-Audio through MLX-Audio

This is the only verified combination found that satisfies both requirements:

1. arbitrary/general environmental sound extraction; and
2. an explicit Apple Silicon accelerated runtime.

MLX-Audio documents `separate()`, chunked `separate_long()`, and streaming output. Its own M-series benchmark table is not chip-specific and does not publish peak memory, so it should not be treated as a performance guarantee for this M5 Air.

For 16 GB unified memory:

- Start with [`sam-audio-small-fp16`](https://huggingface.co/mlx-community/sam-audio-small-fp16), approximately 1.20 GB of weights.
- Do not start with [`sam-audio-large-fp16`](https://huggingface.co/mlx-community/sam-audio-large-fp16/tree/main), whose published repository is 6.08 GB before runtime activations.
- Use 5-10 second chunks and process only low-confidence SoundAnalysis regions.
- Benchmark while YOLO is active; both MLX and MPS use the Apple GPU/unified-memory pool.

The MLX-Audio runtime is MIT licensed, but its SAM-Audio checkpoint inherits Meta's separate SAM model terms. The Hugging Face model card reports `License: other`; model use and redistribution must be checked against the upstream SAM license.

### AudioSep

[AudioSep](https://github.com/Audio-AGI/AudioSep) is open-domain text-conditioned environmental separation and is semantically appropriate. Its official runtime supports CUDA or CPU, not MPS, MLX, Core ML, or ONNX. It can therefore run on an Apple Silicon CPU in principle, but that is ordinary CPU compatibility rather than Apple-specific acceleration.

### CLAPSep

[CLAPSep](https://github.com/Aisaka0v0/CLAPSep) is also query-conditioned target extraction. Its official training/evaluation code selects a CUDA accelerator when requested and CPU otherwise. No MPS, MLX, Core ML, or ONNX deployment is documented. It is less product-ready than MLX-Audio's SAM-Audio path.

## Recommended project architecture

```text
decoded video
├── frames → YOLO → PyTorch MPS
└── audio windows → Apple SoundAnalysis
    ├── confident result → emit event
    └── ambiguous selected window
        → SAM-Audio Small FP16 via MLX (prompt per target)
        → classify original + separated waveform
        → fuse results
```

Run the separator asynchronously and preserve the original-audio classification. Separation can introduce artifacts, and prompting once per candidate target multiplies compute cost.

## Proposed prototype gate

Before making SAM-Audio a normal dependency:

1. Test `sam-audio-small-fp16` on the four challenge WAV files with prompts for cat, dog, engine, and race car.
2. Record cold-load time, per-10-second processing time, process RSS, system memory pressure, and output quality.
3. Run the same test while YOLO is processing video on MPS and compare video FPS.
4. Keep the integration only if separated-audio classification recovers misses without unacceptable false positives or video slowdown.

## Primary sources

- [Meta SAM-Audio official repository](https://github.com/facebookresearch/sam-audio)
- [Meta SAM-Audio announcement](https://ai.meta.com/blog/sam-audio/)
- [MLX-Audio repository and SAM-Audio usage](https://github.com/Blaizzy/mlx-audio#sam-audio-source-separation)
- [MLX-Audio SAM-Audio implementation guide](https://github.com/Blaizzy/mlx-audio/tree/main/mlx_audio/sts/models/sam_audio)
- [SAM-Audio Small FP16 MLX checkpoint](https://huggingface.co/mlx-community/sam-audio-small-fp16)
- [Apple MLX repository](https://github.com/ml-explore/mlx)
- [Apple MLX unified-memory documentation](https://ml-explore.github.io/mlx/build/html/usage/unified_memory.html)
- [AudioSep official repository](https://github.com/Audio-AGI/AudioSep)
- [CLAPSep official repository](https://github.com/Aisaka0v0/CLAPSep)
- [sherpa-onnx macOS and source-separation documentation](https://k2-fsa.github.io/sherpa/onnx/source-separation/models.html)
- [Apple SoundAnalysis documentation](https://developer.apple.com/documentation/soundanalysis/)
