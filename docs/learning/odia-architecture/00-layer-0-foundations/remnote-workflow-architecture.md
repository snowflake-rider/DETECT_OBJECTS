- Where does the main ODIA application code live? >>A)
  - `src/detect_objects/`
    - This package contains the code that runs the application.
  - `tests/`
  - `docs/`
  - `bootstrap/`

- What happens first when you run `python -m detect_objects`? >>A)
  - Python opens the package's `__main__.py`
    - `-m` runs the package through its special entry file.
  - Python starts the camera directly
  - Python runs every test
  - Python opens the documentation

- What is the main job of the setup TUI? >>A)
  - Collect the user's device, model, and theme choices
    - The TUI gathers the settings needed before the system starts.
  - Perform every camera detection
  - Train a new YOLO model
  - Replace the runtime

- What does `Context` hold? >>A)
  - The choices returned by the setup TUI
    - The runtime reads the selected settings from the context.
  - Live camera frames
  - Git commit history
  - Test failures

- What is the main job of `main.py`? >>A)
  - Put the top-level application steps in order
    - It connects setup, preparation, running, and cleanup in a clear sequence.
  - Perform all Whisper calculations itself
  - Store model weights
  - Draw every camera frame

- Why is `LocalRuntime` called a coordinator? >>A)
  - It connects the main parts and controls when they prepare, run, and stop
    - A coordinator manages the parts without doing every low-level job itself.
  - It only changes terminal colors
  - It only reads documentation
  - It replaces the TUI

- What happens during `runtime.prepare()`? >>A)
  - Models and devices are prepared before active detection begins
    - Preparation loads resources and opens the microphone and camera side.
  - All resources are permanently deleted
  - The Git repository is cloned
  - Only the UI theme changes

- What happens during `runtime.run()`? >>A)
  - Voice recognition and camera detection start working
    - The application begins its active microphone and camera work.
  - The project documentation is rebuilt
  - Python installs itself
  - The setup TUI starts for the first time

- What are the two main working sides of the local runtime? >>A)
  - Voice recognition and camera detection
    - Whisper handles speech while YOLO handles camera detection.
  - Git and documentation
  - Tests and bootstrap scripts
  - Theme selection and package installation

- How do recognized class names move from the voice side to the camera side? >>A)
  - Through `class_names_queue`
    - The queue carries the latest class-name list to the camera side.
  - Through `docs/`
  - Through the UI theme
  - Through a model weight file

- Why does voice recognition use a separate thread? >>A)
  - So voice listening and camera detection can continue at the same time
    - The camera does not need to wait for each microphone operation.
  - So Python can find `__main__.py`
  - So the documentation opens faster
  - So the model files become smaller

- Which sequence best describes one complete local ODIA run? >>A)
  - Command ➡️ setup TUI ➡️ `Context` ➡️ prepare ➡️ run ➡️ close
    - This follows the application from startup choices through safe cleanup.
  - Camera ➡️ tests ➡️ Git ➡️ setup TUI
  - Close ➡️ install Python ➡️ microphone ➡️ command
  - Documentation ➡️ model file ➡️ tests ➡️ camera
