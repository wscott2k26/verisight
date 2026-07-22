# Build the premium Vite frontend.
FROM node:22-alpine AS frontend
WORKDIR /frontend

COPY package.json package-lock.json ./
RUN npm install --registry=https://registry.npmjs.org/

COPY index.html vite.config.js postcss.config.js tailwind.config.js ./
COPY src ./src
COPY public ./public
RUN npm run build

# Run FastAPI and serve the compiled frontend from the same origin.
FROM python:3.12-slim AS runtime

ARG REQUIREMENTS_FILE=requirements.txt

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STATIC_DIR=/app/dist \
    HF_HOME=/var/data/huggingface

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements*.txt /tmp/requirements/

# The neural build uses PyTorch's CPU-only wheel to avoid multi-gigabyte CUDA layers.
RUN if [ "$REQUIREMENTS_FILE" = "requirements.txt" ]; then \
      pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.6.0" && \
      grep -v '^torch' /tmp/requirements/requirements.txt > /tmp/requirements/production-no-torch.txt && \
      pip install -r /tmp/requirements/production-no-torch.txt; \
    else \
      pip install -r "/tmp/requirements/$REQUIREMENTS_FILE"; \
    fi

COPY backend/app ./app
COPY --from=frontend /frontend/dist ./dist

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
  CMD curl --fail "http://127.0.0.1:${PORT:-10000}/api/health" || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --proxy-headers --forwarded-allow-ips '*' --workers 1"]
