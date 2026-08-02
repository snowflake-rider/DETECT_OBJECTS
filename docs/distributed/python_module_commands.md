# Running Python modules

## Why the command failed

The terminal showed:

```text
ModuleNotFoundError: No module named 'detect_objects'
```

The `(base)` environment used Miniconda Python 3.14. This project uses Python
3.11 and stores its package inside the `src` directory:

```text
detect_objects/                         project directory
└── src/
    └── detect_objects/                 Python package
        └── distributed/                subpackage
            └── whisper_node.py         module
```

The base Python did not have this package installed, so it could not find
`detect_objects`.

## What `python -m` means

`-m` means **run a Python module**.

```shell
python -m detect_objects.distributed.whisper_node
```

Python reads the dotted name from left to right:

| Name | Meaning |
| --- | --- |
| `detect_objects` | Main package |
| `distributed` | Subpackage inside it |
| `whisper_node` | `whisper_node.py` module |

Python finds that module using the same search system used by `import`. It then
runs the module as the main program. This makes the following block run:

```python
if __name__ == "__main__":
    raise SystemExit(main())
```

## Recommended command

Run the command from the project directory with `uv run`. `uv` selects the
project's Python 3.11 environment and makes the local package available.

```shell
uv run python -m detect_objects.distributed.whisper_node \
  --yolo-address http://192.168.1.10:8000 \
  --microphone-id 4 \
  --model-name medium
```

Replace `192.168.1.10` with the real IP address of the YOLO machine.

The backslash (`\`) tells the shell that the command continues on the next
line. The same command can be written on one line:

```shell
uv run python -m detect_objects.distributed.whisper_node --yolo-address http://192.168.1.10:8000 --microphone-id 4 --model-name medium
```

## YOLO-machine command

Run this on the machine with the camera:

```shell
uv run python -m detect_objects.distributed.yolo_node \
  --host 0.0.0.0 \
  --port 8000 \
  --camera-index 0
```

`0.0.0.0` means the server accepts connections through any network address on
the YOLO machine. The Whisper machine connects using the YOLO machine's real IP
address, not `0.0.0.0`.

## Choosing a microphone ID

`--microphone-id` must point to an input device, not a speaker. List the audio
devices with:

```shell
uv run python -c "import sounddevice as sd; print(sd.query_devices())"
```

Each line starts with its device ID. A device with `1 in` or more can record
audio. A device with `0 in` is not a microphone.

For example:

```text
> 3 MacBook Air Microphone, Core Audio (1 in, 0 out)
< 4 MacBook Air Speakers, Core Audio (0 in, 2 out)
```

Here, `3` is a valid microphone ID and `4` is only an output device. The `>`
marker shows the default input and `<` shows the default output.

## Activated environment alternative

Instead of writing `uv run` each time, activate the project environment:

```shell
source .venv/bin/activate
python -m detect_objects.distributed.whisper_node --help
```

The prompt should show the project environment instead of `(base)`. Run
`deactivate` when finished.

## Check before using hardware

Use `--help` to confirm that Python can find the module without starting a
microphone, camera, or model:

```shell
uv run python -m detect_objects.distributed.whisper_node --help
uv run python -m detect_objects.distributed.yolo_node --help
```
