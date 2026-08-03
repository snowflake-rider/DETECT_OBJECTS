# Session story prototype

The Desktop app can collect YOLO detections that match the latest typed or
Whisper instruction and turn the session into a short visual story.

## Demo flow

1. Confirm that Codex CLI is installed and authenticated with
   `codex login status`.
2. Start the ODIA Desktop app and start Whisper listening.
3. Say an object instruction such as `사람을 찾아줘`.
4. Let the requested object appear in the camera. Matching frames are saved
   with a three-second cooldown.
5. Click **Story**. The UI stays responsive while Codex reads `events.json`
   and the session snapshots.
6. The generated title, short story, and one representative snapshot appear
   in the command dock.

Session artifacts are written under `outputs/story_sessions/<session-id>/`:

```text
events.json
snapshots/*.png
story.json
```

Codex runs ephemerally with a read-only sandbox. Story generation requires at
least one matching snapshot and uses the account already authenticated by the
local Codex CLI.
