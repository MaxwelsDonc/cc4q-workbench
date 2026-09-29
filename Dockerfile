# CC4Q Workbench — all-in-one image (demo UI + full pipeline CLI).
#
#   docker build -t cc4q-workbench .
#   docker run -p 8501:8501 cc4q-workbench
#
# The image does NOT contain the model checkpoints; the entrypoint fetches
# them from the GitHub release (best-effort). To skip that, run with
#   -e CC4Q_SKIP_MODEL_DOWNLOAD=1
# or pre-mount them:
#   docker run -p 8501:8501 -v "$PWD/models_checkpoints:/app/models_checkpoints" cc4q-workbench

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CC4Q_DEVICE=cpu

# CPU-only torch first (avoids multi-GB CUDA wheels), then everything else.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

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
