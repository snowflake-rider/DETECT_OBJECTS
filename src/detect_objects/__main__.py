"""Run ODIA with ``python -m detect_objects``."""

# Command: uv run python -m detect_objects
# - uv run uses this project's Python environment.
# - -m tells Python to run the detect_objects package.
# - Python starts this __main__.py file for that package.

# The dot means "inside the current detect_objects package."
# This imports main() from main.py, where the real workflow lives.
from .main import main

# This is true when Python runs this file as the package entry point.
if __name__ == "__main__":
    # First, main() runs the application and returns a number.
    # SystemExit then ends Python and sends that number to the terminal.
    # 0 normally means success; a nonzero number normally means a problem.
    raise SystemExit(main())
