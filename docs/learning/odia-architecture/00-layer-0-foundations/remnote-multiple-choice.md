Where does the main ODIA application code live? >>A)
- `src/detect_objects/`
  - This package contains the main application code.
- `tests/`
- `docs/`
- `bootstrap/`

What are the jobs of `__main__.py`, `main.py`, and `runtime.py`? >>A)
- Entry point; top-level order; runtime coordination
  - `__main__.py` starts the package, `main.py` orders the workflow, and `runtime.py` coordinates the working parts.
- Model loading; testing; documentation
- TUI drawing; SSH connection; package installation
- Camera capture; audio recording; theme selection

What is the difference between `src/`, `tests/`, and `docs/`? >>A)
- Application code; code checks; explanations
  - `src/` holds the application, `tests/` verifies behavior, and `docs/` explains the project.
- Explanations; application code; model files
- Tests; setup scripts; application code
- Model files; documentation; code checks

What does `python -m detect_objects` mean? >>A)
- Find the `detect_objects` package and run its `__main__.py`
  - The `-m` flag runs a package or module by its Python name.
- Open `main.py` as a text file
- Install the `detect_objects` package
- Run every Python file in the project

Which path correctly describes application startup? >>A)
- `python -m detect_objects` ➡️ `__main__.py` ➡️ `main.py` ➡️ `main()`
  - The `-m` flag enters through `__main__.py`, which imports and calls `main()`.
- `python -m detect_objects` ➡️ `runtime.py` ➡️ `tests/`
- `python -m detect_objects` ➡️ `docs/` ➡️ `main()`
- `python -m detect_objects` ➡️ camera ➡️ `__main__.py`

Why is `__main__.py` intentionally small? >>A)
- Its job is only to enter the package and call `main()`
  - The actual application workflow belongs in `main.py`.
- Python does not allow functions inside `__main__.py`
- It only stores model files
- It exists only for tests

What does `raise SystemExit(main())` do? >>A)
- Run `main()` and return its result as the program's exit status
  - An exit status of `0` normally means success.
- Stop the application before `main()` runs
- Restart `main()` forever
- Delete the runtime after an error

What does the setup TUI collect from the user? >>A)
- Device, model, and theme choices
  - These choices are returned for the runtime to use.
- Test results and Git history
- SSH passwords and network packets
- Python source files and documentation

What is `Context` in this project? >>A)
- An object holding the choices returned by the setup TUI
  - `LocalRuntime` receives this object and uses its selected settings.
- A thread that listens to the microphone
- A queue containing camera frames
- A model that detects objects

What is the difference between `runtime.prepare()` and `runtime.run()`? >>A)
- `prepare()` loads and opens resources; `run()` starts voice and camera work
  - Preparation happens before the active detection loops begin.
- `prepare()` closes resources; `run()` installs Python
- `prepare()` starts tests; `run()` writes documentation
- They always perform exactly the same job

Why is `runtime.close()` inside a `finally` block? >>A)
- To release resources after normal shutdown, `Ctrl+C`, or an error
  - `finally` runs when the `try` block finishes, including many error cases.
- To load the models twice
- To prevent `main()` from starting
- To create another camera thread

Why is `LocalRuntime` called a coordinator? >>A)
- It creates the main parts and tells them when to prepare, run, and stop
  - It connects the parts instead of performing every low-level job itself.
- It only changes terminal colors
- It only stores documentation
- It replaces all manager classes

What do the Whisper, text, and camera managers do? >>A)
- Recognize words; convert words to class names; perform camera detection
  - Together they move from microphone audio to YOLO class selection and detection.
- Detect objects; install models; run tests
- Select themes; open SSH; write JSON
- Close Python; draw folders; manage Git

What does `class_names_queue` carry, and where does it go? >>A)
- The latest YOLO class names from the voice side to the camera side
  - An example is `["person", "cup", "chair"]`.
- Camera frames from the camera to the microphone
- Model files from tests to docs
- Theme colors from runtime to Git

What does `shutdown_event` tell running code? >>A)
- It is time to stop
  - Running loops can check the event and finish cleanly.
- A new model must be downloaded
- The microphone volume is too low
- The queue contains a new class

Why does voice work use a separate thread? >>A)
- So voice listening and camera detection can continue at the same time
  - The camera does not need to wait for each microphone operation to finish.
- So Python can find __main__.py
- So documentation loads faster
- So the TUI can install Git

Which sequence best describes one complete ODIA run? >>A)
- Command ➡️ setup TUI ➡️ `Context` ➡️ `prepare()` ➡️ `run()` ➡️ `close()`
  - This follows the application from startup through cleanup.
- Tests ➡️ docs ➡️ bootstrap ➡️ command
- Camera ➡️ installation ➡️ Git ➡️ `Context`
- Close ➡️ prepare ➡️ command ➡️ setup TUI
