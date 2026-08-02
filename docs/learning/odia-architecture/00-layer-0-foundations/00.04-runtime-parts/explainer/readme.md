# 00.04 — Runtime parts

`LocalRuntime` is the coordinator in `src/detect_objects/runtime.py`.

A coordinator does not perform every job itself. It creates the parts and
tells them when to prepare, run, and stop.

## Main parts

| Part | Simple job |
| --- | --- |
| `Context` | Holds the choices from the TUI |
| `LocalRuntime` | Connects and controls the main parts |
| `Whisper_Audio_Manager` | Listens to the microphone and finds words |
| `Text_Manager` | Converts recognized words into YOLO class names |
| `Camera_Manager` | Runs the camera and YOLO detection |
| `class_names_queue` | Passes the latest class names to the camera side |
| `shutdown_event` | Tells running code that it is time to stop |

Example class names in the queue could look like:

```python
["person", "cup", "chair"]
```

## Very simple data flow

```text
microphone
    -> Whisper text
    -> class names
    -> queue
    -> camera uses the new classes
```

The voice work runs in a separate thread. This lets the camera keep running
while the microphone is listening.

For Layer 0, remember only this:

> The runtime owns the parts, and the queue carries class names from voice to
> camera.
