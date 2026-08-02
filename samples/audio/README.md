# Audio classification samples

These clips are small fixtures for manually testing the configured Apple
SoundAnalysis labels. They are not a representative accuracy benchmark. Each
source was converted to 16-bit, 16 kHz, mono PCM WAV without trimming.

| Local file | Expected labels | Source and license |
|---|---|---|
| `cat_meow.wav` | `cat_meow` | [Meow of a pleading cat](https://commons.wikimedia.org/wiki/File:Meow_of_a_pleading_cat.oga) by Heismark, public domain |
| `dog_bark.wav` | `dog_bark` | [Ladrido perro](https://commons.wikimedia.org/wiki/File:Ladrido_perro.ogg) by Edo.pt2, [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `engine_revving_lada.wav` | `engine`, possibly `engine_accelerating_revving` | [Starting up Lada 1200L Zhiguli Engine](https://commons.wikimedia.org/wiki/File:Starting_up_Lada_1200L_Zhiguli_Engine.webm), recorded by Antti Makkonen for Sounds of Changes, [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) |
| `race_car_audi_r8.wav` | `race_car`, `engine_accelerating_revving`, `engine` | [Audi R8 (2000)](https://commons.wikimedia.org/wiki/File:Audi_R8_(2000).ogg), recorded by Edvvc, [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) |

The converted Lada clip is attributed to Sounds of Changes and Antti Makkonen.
The converted Audi R8 clip is attributed to Edvvc and remains available under
CC BY-SA 3.0. See the linked source pages for the complete license statements.

## Challenging mixtures

These files combine or degrade the source clips above to exercise overlapping
sound detection and failure cases. They remain subject to the attribution and
share-alike terms of their component recordings.

| Local file | Construction | Result at the initial `0.5` thresholds |
|---|---|---|
| `challenge_cat_over_engine.wav` | Quiet cat mixed over a louder Lada engine | Detects both cat and engine |
| `challenge_dog_over_race_car.wav` | Quiet dog mixed over the Audi R8 | Detects vehicle labels but misses the dog |
| `challenge_cat_dog_overlap.wav` | Cat and dog overlap, with the dog quieter | Detects the cat but misses the dog |
| `challenge_race_car_with_noise.wav` | Quiet Audi R8 mixed with pink noise | Misses all configured vehicle labels |

These observations are smoke-test results, not accuracy measurements. They are
useful starting points for evaluating window duration and per-label thresholds.
