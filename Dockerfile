# CC4Q Workbench — all-in-one image (demo UI + full pipeline CLI), CPU or GPU.
#
#   CPU (default, small image):
#     docker build -t cc4q-workbench .
#     docker run -p 8501:8501 cc4q-workbench
#
#   GPU (CUDA wheels; needs an NVIDIA driver + nvidia-container-toolkit on
#   the host, and runs on CPU-only hosts too — just larger):
#     docker build --build-arg TORCH_CHANNEL=gpu -t cc4q-workbench:gpu .
#     docker run --gpus all -p 8501:8501 cc4q-workbench:gpu
#
# No CC4Q_DEVICE is baked in: the app auto-detects CUDA at runtime
# (escape hatch: -e CC4Q_DEVICE=cpu). Models are fetched at container start.

FROM python:3.11-slim

WORKDIR /app

# TORCH_CHANNEL=cpu (default) -> torch CPU wheels, ~2.5 GB image.
# TORCH_CHANNEL=gpu           -> torch 2.14.0+cu126 wheels; the bundled
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

RUN chmod +x docker-entrypoint.sh

EXPOSE 8501

# Default: the Streamlit demo. Override with e.g.
#   docker run --entrypoint python cc4q-workbench scripts/02_extract_code_comment_pairs.py config/examples.yaml
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["streamlit", "run", "demo/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
