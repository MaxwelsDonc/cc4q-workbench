# CC4Q Workbench — all-in-one image (web workbench + full pipeline CLI).
#
#   docker build -t cc4q-workbench .
#   docker run -p 8501:8501 cc4q-workbench
#
# No CC4Q_DEVICE is baked in: the app auto-detects CUDA at runtime if the
# host exposes a GPU (escape hatch: -e CC4Q_DEVICE=cpu). Models are fetched
# at container start. Every push is build-verified by CI, so this file does
# not need manual verification.

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# git: live repo analysis clones with `git clone --depth 1`.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

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
#   docker run --entrypoint cc4q cc4q-workbench build --repo examples/tiny_repo --output-dir /tmp/out
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["cc4q", "serve", "--host", "0.0.0.0", "--port", "8501"]
