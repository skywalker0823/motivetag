FROM python:3.11-slim

# Debian's security fixes, which reach apt before a rebuilt python image does (Trivy
# fails the build on a fixed HIGH/CRITICAL). CI passes the ISO week, so the build cache
# keeps this layer for at most a week.
ARG SECURITY_REFRESH=""
RUN echo "security updates: ${SECURITY_REFRESH}" \
    && apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

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

# The commit this image was built from; Sentry tags errors with it as the release.
ARG GIT_SHA=""
ENV GIT_SHA=$GIT_SHA

RUN useradd --system --no-create-home app && chmod +x docker-entrypoint.sh
USER app

EXPOSE 3000
ENTRYPOINT ["./docker-entrypoint.sh"]
