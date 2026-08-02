# 00.03 — Main workflow

The top-level workflow lives in `src/detect_objects/main.py`.

It follows this order:

```text
1. Open the setup TUI
2. Receive the user's choices
3. Create the runtime
4. Prepare the models and devices
5. Run voice and camera
6. Close everything
```

## Step 1: setup

`run_app()` opens the terminal interface. The user chooses devices, models,
and a theme.

When setup finishes, `run_app()` returns a `Context`.

## Step 2: create the runtime

`LocalRuntime(context)` receives those choices. It will use them to build the
voice and camera parts.

## Step 3: prepare

`runtime.prepare()` loads models and opens devices. The startup screen shows
the progress messages.

## Step 4: run

`runtime.run()` starts voice recognition and camera detection.

## Step 5: close

`runtime.close()` releases the microphone, camera, and model resources.

It is inside `finally`, so Python tries to close these resources even if the
user presses `Ctrl+C` or an error happens.

## One-sentence version

> The TUI collects choices, the runtime prepares and runs the system, and the
> `finally` block closes it safely.
