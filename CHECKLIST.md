# Checklist

- [ ] Statistical comparison for different vision models
- [ ] Performance comparison between local and distributed execution

## Bootstrap

- [ ] Conda choice portable
    - [ ] Mac
    - [ ] Windows
    - [ ] Existing Conda path
    - [ ] Private Miniconda fallback path
- [ ] uv env portable
    - [x] Mac
    - [ ] Windows

### Tomorrow — Windows (2026-08-03)

- [ ] Clone the `uv-env` branch on a Windows computer
    - [ ] Run `.\bootstrap\setup.ps1` from PowerShell
    - [ ] Check the arrow keys, Enter, number shortcuts, `Q`, and screen restoration
    - [ ] Choose `uv` and complete installation, model download, verification, and ODIA launch
    - [ ] Confirm generated environments, tools, and caches remain inside `.odia/`
    - [ ] Test Conda with an existing installation and with the Miniconda fallback
    - [ ] Write down any Windows-specific errors or missing system requirements

### Later — Linux

- [ ] Run `./bootstrap/setup.sh` on a Linux computer
- [ ] Test `uv` and Conda, including the Miniconda fallback
    - [ ] Confirm audio dependencies and ODIA device setup work on Linux

## Distributed test at home

- [ ] Add a video streaming source for the app (e.g., YouTube or local MP4 playback)
- [ ] Use this Mac for the camera and YOLO
- [ ] Use `Kafka-MBP` for the microphone and Whisper
- [ ] Clone the `uv-env` branch into `~/Git/Experiment/detect_objects` on `Kafka-MBP`
- [ ] Prepare the remote `uv` environment
- [ ] Find the remote Mac's microphone ID
- [ ] Start the YOLO node on this Mac using port `8000`
- [ ] Start the Whisper node with this Mac's HTTP address
- [ ] Speak into `Kafka-MBP` and confirm YOLO receives the class names
