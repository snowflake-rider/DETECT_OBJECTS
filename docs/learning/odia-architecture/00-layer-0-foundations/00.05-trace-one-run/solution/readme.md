# 00.05 — Solution

## Exercise 1

```text
5  LocalRuntime.run() starts voice and camera.
1  python -m detect_objects runs __main__.py.
6  runtime.close() releases resources.
3  run_app() returns the user's Context.
4  LocalRuntime.prepare() loads models and opens devices.
2  __main__.py calls main().
```

## Exercise 2

1. `Context` holds the choices made in the TUI.
2. `LocalRuntime` connects and controls the voice and camera parts.
3. `class_names_queue` carries the latest YOLO class names.
4. `shutdown_event` means the running work should stop.
5. `finally` makes cleanup run after normal shutdown, `Ctrl+C`, or an error.

## Exercise 3: sample answer

> `python -m detect_objects` runs `__main__.py`, which calls `main()`. The TUI
> collects the user's choices and returns a `Context`. `LocalRuntime` uses that
> context to prepare the microphone, camera, and models. It then runs voice and
> camera work. When the program ends, `close()` releases the resources.

You do not need to repeat this word for word. Your own clear explanation is
better.
