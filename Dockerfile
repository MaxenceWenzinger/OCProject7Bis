# REST API of the RAG (api/app.py).
#
# The image is self-contained (code, dependencies and the bge-m3 model).
# The database stays on the host (or any other server): give its address in DATABASE_URL.
# See the "Docker" section of the README for the build and run commands.

FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.14 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first, in their own layer: it is only rebuilt when pyproject.toml or uv.lock change.
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

ENV PATH="/app/.venv/bin:$PATH" \
    HF_HOME=/models/huggingface

# bge-m3 goes in the image (about 2.3 GB), in its own layer, before the code: changing the code
# doesn't download it again. Only the files of the PyTorch model are kept (not the ONNX copy).
RUN python -c "from huggingface_hub import snapshot_download; \
snapshot_download('BAAI/bge-m3', allow_patterns=['*.json', '*.model', '*.pt', 'pytorch_model.bin'])"

# The model is in the image: never try to reach the Hugging Face Hub at run time.
ENV HF_HUB_OFFLINE=1

COPY config.py database.py ./
COPY models ./models
COPY api ./api
COPY scripts ./scripts

RUN useradd --create-home app
USER app

EXPOSE 8000

# Loading bge-m3 at startup takes a while.
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
