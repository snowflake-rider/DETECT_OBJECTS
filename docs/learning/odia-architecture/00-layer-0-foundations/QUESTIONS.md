# Layer 0 questions

These questions check whether you understand the Layer 0 material.

## How we use this file

1. I ask one question at a time.
2. You answer using your own words.
3. If the answer is unclear, we review it and try again.
4. We check the question after you understand it.
5. Layer 0 is cleared when every question is checked.

You do not need to use the exact words from the lessons.

**Layer status:** Cleared on 2026-08-03

## Project map

- [x] **Q1.** Where does the main application code live?
- [x] **Q2.** What are the jobs of `__main__.py`, `main.py`, and `runtime.py`?
- [x] **Q3.** What is the difference between `src/`, `tests/`, and `docs/`?

## Python entry point

- [x] **Q4.** What does `python -m detect_objects` mean?
- [x] **Q5.** Describe the path from the terminal command to `main()`.
- [x] **Q6.** Why is `__main__.py` very small?
- [x] **Q7.** What does `raise SystemExit(main())` do?

## Main workflow

- [x] **Q8.** What does the setup TUI collect from the user?
- [x] **Q9.** What is a `Context`, and where does it come from?
- [x] **Q10.** What is the difference between `runtime.prepare()` and
  `runtime.run()`?
- [x] **Q11.** Why is `runtime.close()` placed inside a `finally` block?

## Runtime parts

- [x] **Q12.** Why do we call `LocalRuntime` a coordinator?
- [x] **Q13.** What jobs do the Whisper, text, and camera managers perform?
- [x] **Q14.** What data goes into `class_names_queue`, and where does it go?
- [x] **Q15.** What does `shutdown_event` tell the running code?
- [x] **Q16.** Why does the voice work use a separate thread?

## Complete explanation

- [x] **Q17.** Explain one complete run, starting with
  `python -m detect_objects` and ending with cleanup.
