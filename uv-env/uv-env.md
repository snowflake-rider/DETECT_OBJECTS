# UV environment management
- python-version: 3.11
- dependencies: requirement.txt

## Easy Run

```shell
# 1. Install dependencies (--locked use existing uv.lock)
uv sync
# 2. Activate Environment
source .venv/bin/activate
# 3. Run the project
uv run python main.py
```