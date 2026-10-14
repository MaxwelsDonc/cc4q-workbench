# CC4Q Workbench — all-in-one image (demo UI + full pipeline CLI), CPU or GPU.
#
#   CPU (default, small image):
#     docker build -t cc4q-workbench .
#     docker run -p 8501:8501 cc4q-workbench
#
#   GPU (CUDA wheels; needs an NVIDIA driver + nvidia-container-toolkit on
#   the host, and runs on CPU-only hosts too — just larger):
#     docker build --build-arg TORCH_CHANNEL=cu126 -t cc4q-workbench:gpu .
#     docker run --gpus all -p 8501:8501 cc4q-workbench:gpu
#
# No CC4Q_DEVICE is baked in: the app auto-detects CUDA at runtime
# (escape hatch: -e CC4Q_DEVICE=cpu). Models are fetched at container start.

FROM python:3.11-slim

WORKDIR /app

# TORCH_CHANNEL=cpu  (default) -> torch CPU wheels, ~2.5 GB image.
# TORCH_CHANNEL=cu126          -> torch 2.14.0+cu126 CUDA wheels; the bundled
#                                nvidia-*-cu12 runtime libraries make the
#                                image GPU-capable, ~7 GB.
ARG TORCH_CHANNEL=cpu

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# git: live repo analysis clones with `git clone --depth 1`.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
        --index-url "https://download.pytorch.org/whl/${TORCH_CHANNEL}" \
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
