- You run `python -m detect_objects`. Which file does Python look for inside the package? >>A)
  - `__main__.py`
    - The `-m` flag enters a package through its `__main__.py` file.
  - `runtime.py`
  - `context.py`
  - `test_main.py`

- The setup TUI finishes successfully. What does it pass into `LocalRuntime`? >>A)
  - A `Context` containing the user's selections
    - The context carries choices such as devices, models, and the UI theme.
  - A camera frame
  - A completed test report
  - An SSH connection

- The application needs to load models and open devices before detection starts. Which call handles that stage? >>A)
  - `runtime.prepare()`
    - Preparation happens before the active camera and voice work begins.
  - `runtime.close()`
  - `run_app()`
  - `queue.get_nowait()`

- The camera must keep detecting while the microphone listens. Which design makes that possible? >>A)
  - Run the voice work in a separate thread
    - The camera does not have to wait for each microphone operation to finish.
  - Run the tests before every frame
  - Put the camera inside `docs/`
  - Start `main()` twice

- Voice recognition finds `"cup"` and `"person"`. How do those class names reach the camera side? >>A)
  - They are placed into `class_names_queue`
    - The queue passes the latest class-name list from voice to camera.
  - They are written into `__main__.py`
  - They are stored in the UI theme
  - They are sent to the test directory

- The user presses `Ctrl+C` while detection is running. Which block still attempts cleanup? >>A)
  - The `finally` block
    - `finally` runs after normal completion and many error or interruption cases.
  - The `import` block
  - The argument parser
  - The model configuration file

- Which responsibility belongs to `LocalRuntime`? >>A)
  - Coordinate preparation, running, and cleanup of the main parts
    - A coordinator connects the parts and controls their lifecycle.
  - Draw every TUI widget itself
  - Store every YOLO model file
  - Replace Python's module system

- A running loop sees that `shutdown_event` is set. What should it do? >>A)
  - Finish its work and stop cleanly
    - The event is a shared signal that shutdown has started.
  - Download another model
  - Empty the documentation folder
  - Start another microphone thread

- Which sequence correctly describes voice data reaching object detection? >>A)
  - Microphone ➡️ Whisper ➡️ text manager ➡️ queue ➡️ camera
    - Speech becomes text, then class names, and then reaches the camera through the queue.
  - Camera ➡️ tests ➡️ Git ➡️ microphone
  - Documentation ➡️ model file ➡️ TUI theme
  - Queue ➡️ bootstrap ➡️ SSH ➡️ camera

- You want to add a beginner explanation without changing application behavior. Where should it go? >>A)
  - `docs/`
    - Documentation belongs in `docs/`, while application behavior belongs in `src/`.
  - `model_artifacts/`
  - `tests/`
  - `src/detect_objects/__main__.py`

- Which statement correctly compares `main.py` and `runtime.py`? >>A)
  - `main.py` orders the top-level flow; `runtime.py` coordinates the working parts
    - The main file stays small while the runtime owns detailed preparation and resource control.
  - Both files only contain tests
  - `main.py` stores model weights; `runtime.py` stores documentation
  - Both files perform exactly the same job

```python
raise SystemExit(main())
```

- Which multi-line rewrite keeps the same basic behavior? >>A)
  ```python
  result = main()
  # Use main's result as the terminal exit status.
  raise SystemExit(result)
  ```
  ```python
  result = main
  # This stores the function without calling it.
  raise SystemExit(result)
  ```
  ```python
  raise SystemExit
  # main() is never used as the exit result.
  main()
  ```
  ```python
  main = SystemExit()
  # This replaces the main function name.
  main()
  ```
