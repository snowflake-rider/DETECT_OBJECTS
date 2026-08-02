# uv environment management

- Python version: 3.11
- Dependency metadata: `pyproject.toml`
- Locked versions: `uv.lock`

## Easy Run

```shell
# Install dependencies and required model weights, then verify the environment.
./bootstrap/uv/setup.sh

# Run the complete application.
UV_PROJECT_ENVIRONMENT=odia-uv uv run odia
```

See [`bootstrap/README.md`](../../bootstrap/README.md) for the Conda path and
new-machine instructions.
