# Multi-label audio tagging on Apple Silicon

Research date: 2026-08-02

## Conclusion

**SAM-Audio is the wrong model for this requirement.** It separates a requested
sound from a mixture, but it does not discover and score every sound. The required
task is **multi-label audio tagging**: one WAV window should yield independent
scores for labels such as `Dog`, `Bark`, `Race car, auto racing`, and `Engine`.

The recommended implementation path is:

1. **Immediately fix the output policy around the existing Apple SoundAnalysis
   backend.** Preserve and print the top-N classifications per window and always
   print configured target-label scores, even below the event threshold. Apply
   thresholds only when deciding whether to emit an application event.
2. **Add EfficientAT `dymn10_as` as the first portable model backend.** It is a
   10.57M-parameter AudioSet tagger with 527 independent sigmoid outputs, 0.58G
   MACs per ten-second clip, and published AudioSet mAP of 0.477-0.478. Its exact
   vocabulary contains `Dog`, `Bark`, `Car`, `Race car, auto racing`, and
   `Engine`. The code and weights are MIT licensed.
3. Benchmark the challenge clips on CPU first, then test a small PyTorch MPS
   adaptation. EfficientAT's upstream CLI explicitly supports CPU and CUDA, not
   MPS, so Apple-GPU correctness and speed must be measured rather than assumed.
4. Consider BEATs Iter3+ AS2M later as a heavier accuracy benchmark, not the
   default. It reaches 0.506 AudioSet mAP but is substantially larger and its
   upstream implementation is not Apple-specific.

This gives the project a native, zero-download default and a stronger open model
without adding TensorFlow or a large transformer as the first new dependency.

## What the current Apple model actually returned

A read-only diagnostic was run against
`samples/audio/challenge_dog_over_race_car.wav` using the existing classifier,
the same 3-second windows, and zero thresholds for the five target labels.

| Window | Highest relevant scores |
|---|---|
| 0.0-3.0 s | `engine` 0.069, `dog` 0.024, `race_car` 0.022, `dog_bark` 0.013 |
| 3.0-6.0 s | `engine_accelerating_revving` 0.700, `engine` 0.622, `race_car` 0.558, `dog` 0.004 |
| 4.5-7.5 s | `engine_accelerating_revving` 0.692, `engine` 0.620, `race_car` 0.534, `dog` 0.029 |
| 6.0-9.0 s | `engine_accelerating_revving` 0.731, `engine` 0.619, `race_car` 0.533, `dog` 0.041, `dog_bark` 0.020 |

So SoundAnalysis already found both sound families. The project currently discards
every configured classification below its per-label threshold, which makes a
valid low-confidence result look like "no output." The dog remains a weak result,
so changing display policy fixes visibility but does not guarantee a correct event
decision.

A separate local AST/MPS experiment on the same mixture was more favorable to the
dog during the 4.5-7.5 second window: `Dog=0.138`, `Bow-wow=0.075`,
`Race car, auto racing=0.061`, and `Accelerating, revving, vroom=0.170`. This
confirms that a second AudioSet backend is worth benchmarking, while also showing
why fixed `0.5` filtering is inappropriate: it would hide all four useful scores.

Apple documents that SoundAnalysis identifies more than 300 sounds and returns
ranked classifications for time ranges. The installed classifier's runtime
vocabulary can be enumerated through `knownClassifications`; this repository has
already verified the exact identifiers `dog_bark`, `race_car`, `engine`, and
`engine_accelerating_revving`. See Apple's [Sound Analysis overview](https://developer.apple.com/documentation/soundanalysis/),
[`SNClassificationResult`](https://developer.apple.com/documentation/soundanalysis/snclassificationresult),
and [`knownClassifications`](https://developer.apple.com/documentation/soundanalysis/snclassifysoundrequest/knownclassifications).

## Model comparison

| Model | Simultaneous multi-label scores? | Relevant vocabulary | Published AudioSet result | Apple Silicon path | License / assessment |
|---|---|---|---:|---|---|
| Apple SoundAnalysis v1 | Yes; ranked labels and confidence by time window | Installed model has exact project labels | Apple does not publish an AudioSet mAP | Native SoundAnalysis/Core ML runtime | Apple SDK/runtime; **keep as default** |
| EfficientAT `dymn10_as` | Yes; upstream applies sigmoid to every logit | Full 527-label AudioSet map, including exact desired labels | 0.477-0.478 mAP | CPU works upstream; MPS needs a small adapter and validation | MIT; **best next backend** |
| BEATs Iter3+ AS2M | Yes; 527 sigmoid probabilities and checkpoint `label_dict` | AudioSet vocabulary | 0.506 mAP | PyTorch CPU; MPS is plausible but not documented by BEATs | MIT; strongest compared supervised model, but heavier |
| AST AudioSet | Yes if the 527 raw logits are passed through sigmoid | Full 527-label AudioSet vocabulary | 0.459 single checkpoint; 0.485 ensemble | PyTorch/Transformers CPU or MPS | BSD-3-Clause; easier packaging than BEATs but less accurate and ~86.6M params |
| PANNs Cnn14 | Yes; clip-level probabilities; frame-capable variants exist | Full 527-label AudioSet vocabulary | 0.431; best reported PANN 0.439 | PyTorch CPU; upstream CLI documents CUDA rather than MPS | MIT; mature but superseded by EfficientAT here |
| YAMNet | Yes; independent logistic scores every 0.96 s | 521-label AudioSet subset includes `Dog`, `Bark`, `Car`, `Race car, auto racing`, and `Engine` | 0.306 mAP | TensorFlow CPU; Apple also provides `tensorflow-metal` | Apache-2.0; tiny (3.7M weights), but weakest accuracy and adds TensorFlow |
| LAION-CLAP | **No, not in the required sense**; it returns audio-text similarities, normally softmaxed across candidate prompts | Open vocabulary chosen at runtime | Zero-shot metrics, not comparable supervised AudioSet mAP | Transformers/PyTorch CPU; generic MPS may work but is not promised by CLAP | Apache-2.0 checkpoint; useful fallback for novel concepts, not primary tagger |

Sources for these rows:

- [EfficientAT official repository](https://github.com/fschmid56/EfficientAT) publishes
  the model sizes, complexity, mAP, pretrained downloads, top-ten inference, and MIT
  license. Its [inference implementation](https://github.com/fschmid56/EfficientAT/blob/main/inference.py)
  applies `torch.sigmoid` independently to the model logits. Its
  [class map](https://github.com/fschmid56/EfficientAT/blob/main/metadata/class_labels_indices.csv)
  contains the exact target labels.
- Microsoft's [BEATs repository](https://github.com/microsoft/unilm/blob/master/beats/README.md)
  provides AudioSet-fine-tuned checkpoints and prints top labels with probabilities;
  [the implementation](https://github.com/microsoft/unilm/blob/master/beats/BEATs.py)
  uses a 527-class head and sigmoid. The [BEATs paper](https://arxiv.org/abs/2212.09058)
  reports 0.506 mAP.
- The [official AST repository](https://github.com/YuanGongND/ast) provides a
  527-logit AudioSet model and reports the results above. The packaged
  [MIT AudioSet checkpoint](https://huggingface.co/MIT/ast-finetuned-audioset-10-10-0.4593)
  is 86.6M parameters and BSD-3-Clause licensed. Use manual sigmoid for multi-label
  scores; do not rely on a single-label softmax pipeline.
- The [PANNs repository](https://github.com/qiuqiangkong/audioset_tagging_cnn)
  publishes 527-class models, per-label output examples, results, and an MIT license.
- Google's [YAMNet documentation](https://github.com/tensorflow/models/blob/master/research/audioset/yamnet/README.md)
  specifies the independent logistic outputs, 0.96-second framing, model size,
  metrics, and 521-label vocabulary. The exact labels are in its
  [class map](https://github.com/tensorflow/models/blob/master/research/audioset/yamnet/yamnet_class_map.csv).
- The [CLAP model documentation](https://huggingface.co/docs/transformers/model_doc/clap)
  defines its outputs as audio-text similarity scores and demonstrates softmax over
  the candidate texts. The [LAION checkpoint card](https://huggingface.co/laion/clap-htsat-fused)
  lists 0.2B parameters and Apache-2.0 licensing.
- PyTorch documents macOS GPU execution through its generic
  [MPS backend](https://docs.pytorch.org/docs/stable/notes/mps.html). This proves the
  runtime exists, not that every upstream model and preprocessing operator works on
  MPS without changes.
- Google lists `Dog`, `Bark`, and `Race car, auto racing` in the official
  [AudioSet label inventory](https://research.google.com/audioset/dataset/index.html).

## Output policy for mixtures

The classifier API should separate **measurement** from **decision**:

```text
window 6.0-9.0 s
top: engine_accelerating_revving=0.731, engine=0.619, race_car=0.533, ...
targets: dog=0.041, dog_bark=0.020, race_car=0.533, engine=0.619
events: race_car, engine                  # thresholded application decision
```

For each WAV:

- use overlapping 1-2 second windows for short barking rather than only a whole-file
  average;
- print top-N labels regardless of threshold;
- always print scores for configured target labels, even when absent from top-N;
- summarize each label using its maximum window score and the winning time range;
- maintain per-class event thresholds because raw confidence values are not equally
  calibrated across classes or models.

Do not softmax the AudioSet outputs: dog and race car must be allowed to score high
at the same time. CLAP's candidate-label softmax is a relative ranking and therefore
does not provide the same semantics.
