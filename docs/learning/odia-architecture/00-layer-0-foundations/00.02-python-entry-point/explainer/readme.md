# 00.02 — Python entry point

This command starts the application:

```bash
uv run python -m detect_objects
```

`-m detect_objects` means:

> Find the `detect_objects` package and run its `__main__.py` file.

## Why are there two main files?

- `__main__.py` is the special file Python looks for because we used `-m`.
- `main.py` is our normal file that contains the `main()` function.

They are connected like this:

```text
python -m detect_objects
        -> __main__.py
        -> main.py
        -> main()
```

The underscores are part of the first filename. They are not decoration:

```text
__main__.py  = special Python entry file
main.py      = normal application file
```

The first part of the flow is:

```text
python -m detect_objects
        |
        v
src/detect_objects/__main__.py
        |
        v
src/detect_objects/main.py
        |
        v
main()
```

`__main__.py` is intentionally small. It imports `main()` and calls it.

```python
raise SystemExit(main())
```

This does two things:

1. `main()` runs the application.
2. `SystemExit` returns the final result to the terminal.

A result of `0` normally means the program ended successfully.

## Check yourself

Explain this sentence in your own words:

> `python -m detect_objects` finds `__main__.py`, which calls `main()`.
