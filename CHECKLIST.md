# Checklist

## Bootstrap

- [ ] conda env portable
    - [ ] Mac
    - [ ] Windows
- [ ] uv env portable
    - [ ] Mac
    - [ ] Windows
- [ ] private Miniconda env portable
    - [x] Mac — installation, imports, verification, and ODIA launch passed
    - [ ] Windows

### Tomorrow — Windows (2026-08-03)

- [ ] Clone the `uv-env` branch on a Windows computer
- [ ] Run `.\bootstrap\setup.ps1` from PowerShell
- [ ] Check the arrow keys, Enter, number shortcuts, `Q`, and screen restoration
- [ ] Choose `uv` and complete installation, model download, verification, and ODIA launch
- [ ] Confirm generated environments, tools, and caches remain inside `.odia/`
- [ ] Test the existing Conda and private Miniconda choices separately
- [ ] Write down any Windows-specific errors or missing system requirements

### Later — Linux

- [ ] Run `./bootstrap/setup.sh` on a Linux computer
- [ ] Test the `uv`, existing Conda, and private Miniconda choices
- [ ] Confirm audio dependencies and ODIA device setup work on Linux

## Distributed test at home

- [ ] Use this Mac for the camera and YOLO
- [ ] Use `Kafka-MBP` for the microphone and Whisper
- [ ] Clone the `uv-env` branch into `~/Git/Experiment/detect_objects` on `Kafka-MBP`
- [ ] Prepare the remote `uv` environment
- [ ] Find the remote Mac's microphone ID
- [ ] Start the YOLO node on this Mac using port `8000`
- [ ] Start the Whisper node with this Mac's HTTP address
- [ ] Speak into `Kafka-MBP` and confirm YOLO receives the class names
