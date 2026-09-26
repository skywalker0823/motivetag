FROM python:3.11-slim

# The app runs from .venv; drop the base image's own pip/setuptools so they can't ship CVEs.
RUN pip install --no-cache-dir uv==0.8.17 \
    && pip uninstall -y pip setuptools wheel

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install dependencies first so code changes don't invalidate this layer.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

RUN useradd --system --no-create-home app && chmod +x docker-entrypoint.sh
USER app

EXPOSE 3000
ENTRYPOINT ["./docker-entrypoint.sh"]
