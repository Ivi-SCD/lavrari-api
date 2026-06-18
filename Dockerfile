FROM python:3.11-slim

WORKDIR /app

# Dependências de sistema do WeasyPrint (Pango/Cairo/GDK-Pixbuf) + fontes.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libffi8 \
        libharfbuzz0b \
        libfribidi0 \
        shared-mime-info \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Instala dependências a partir do lock (reprodutível).
COPY pyproject.toml uv.lock ./
RUN uv export --frozen --no-dev --no-emit-project -o requirements.txt \
    && uv pip install --system --no-cache -r requirements.txt

COPY app/ app/

ENV PORT=8000
EXPOSE 8000

# Code Engine injeta a porta via $PORT.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
