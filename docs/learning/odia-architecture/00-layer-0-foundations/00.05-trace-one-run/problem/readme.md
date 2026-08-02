# 00.05 — Trace one run

This small exercise checks the complete Layer 0 flow.

## Exercise 1: put the steps in order

Write the correct number beside each step:

```text
__  LocalRuntime.run() starts voice and camera.
__  python -m detect_objects runs __main__.py.
__  runtime.close() releases resources.
__  run_app() returns the user's Context.
__  LocalRuntime.prepare() loads models and opens devices.
__  __main__.py calls main().
```

## Exercise 2: explain the main objects

Answer with one short sentence each:

1. What is `Context`?
2. What is `LocalRuntime`?
3. What does `class_names_queue` carry?
4. What does `shutdown_event` mean?
5. Why is `runtime.close()` inside `finally`?

## Exercise 3: one-minute explanation

Explain one application run aloud. Start with the terminal command and finish
with cleanup.

When you finish, compare your answers with the
[solution](../solution/readme.md).
