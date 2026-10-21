# CC4Q Workbench — all-in-one image (web workbench + full pipeline CLI).
#
#   docker run --rm -p 8501:8501 ghcr.io/maxwelsdonc/cc4q-workbench:latest
#
# The two released BERT checkpoints (~835 MB, SHA256-verified) are baked in
# at build time, so the container starts instantly with zero downloads.
# The image is single-flavor and CPU-based; the app auto-detects CUDA at
# runtime if the host exposes a GPU (escape hatch: -e CC4Q_DEVICE=cpu).

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CC4Q_MODEL_DIR=/app/models_checkpoints \
    CC4Q_SKIP_MODEL_DOWNLOAD=1

# git: live repo analysis clones with `git clone --depth 1`.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Released quantum BERT checkpoints (~835 MB, fetched + SHA256-verified +
# extracted into $CC4Q_MODEL_DIR). hub.py is stdlib-only, so this heavy
# layer caches independently of the pip layers below and only rebuilds
# when the checkpoint URLs/checksums change.
COPY cc4q/models/hub.py /tmp/cc4q_hub.py
RUN python -c "import importlib.util; spec = importlib.util.spec_from_file_location('cc4q_hub', '/tmp/cc4q_hub.py'); hub = importlib.util.module_from_spec(spec); spec.loader.exec_module(hub); missing = hub.ensure_checkpoints(model_dir='/app/models_checkpoints'); assert not missing, f'still missing: {missing}'" \
    && rm /tmp/cc4q_hub.py

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
        --index-url "https://download.pytorch.org/whl/cpu" \
        "torch==2.14.0"

COPY requirements.txt demo/requirements-demo.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-demo.txt \
    && python -m spacy download en_core_web_sm

COPY . .
RUN pip install --no-cache-dir -e .

RUN chmod +x docker-entrypoint.sh

EXPOSE 8501

# Default: the CC4Q Web Workbench (Starlette/Uvicorn). Override with e.g.
#   docker run --entrypoint cc4q ghcr.io/maxwelsdonc/cc4q-workbench build --repo examples/tiny_repo --output-dir /tmp/out
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["cc4q", "serve", "--host", "0.0.0.0", "--port", "8501"]
