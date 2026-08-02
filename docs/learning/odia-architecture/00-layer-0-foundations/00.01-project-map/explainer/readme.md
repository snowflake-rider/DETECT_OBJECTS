# 00.01 — Project map

The project is split into folders based on their job.

| Folder | Simple meaning |
| --- | --- |
| `src/detect_objects/` | The application code |
| `tests/` | Checks that the code works |
| `docs/` | Explanations and learning notes |
| `bootstrap/` | Scripts that prepare a new computer |
| `config/` | Model and application settings |
| `model_artifacts/` | Downloaded model files |

## The important part for now

Start inside `src/detect_objects/`.

| Path | Job |
| --- | --- |
| `__main__.py` | Receives the `python -m detect_objects` command |
| `main.py` | Puts the main steps in order |
| `tui/` | Lets the user choose models, devices, and a theme |
| `runtime.py` | Connects the camera and voice parts |
| `camera_cv/` | Camera and object detection code |
| `voice_text_convert/` | Microphone and Whisper code |
| `models/` | Small data objects shared by different parts |

You do not need every filename yet. Remember this smaller map:

```text
command
   -> user setup
   -> runtime
      -> voice
      -> camera
```

## Check yourself

Without looking at the table, answer:

1. Where does the real application code live?
2. Which file puts the main steps in order?
3. Which file connects voice and camera?
