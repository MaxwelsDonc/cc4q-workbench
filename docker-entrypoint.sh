#!/usr/bin/env bash
# CC4Q Workbench container entrypoint.
# Best-effort: fetch the model checkpoints from the GitHub release so the
# demo can classify. If this fails (offline, private repo, no network),
# the demo still starts — Analyze pages show the download instructions.
set -e

if [ "${CC4Q_SKIP_MODEL_DOWNLOAD}" != "1" ]; then
    echo "[entrypoint] ensuring model checkpoints (CC4Q_SKIP_MODEL_DOWNLOAD=1 to skip)…"
    python scripts/download_models.py || \
        echo "[entrypoint] model download failed or incomplete — starting anyway; run 'python scripts/download_models.py' inside the container."
fi

exec "$@"
