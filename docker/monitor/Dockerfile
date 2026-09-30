# ==============================================================================
# Monitor host - Week 05 Lab (Activity 2)
# Python 3.14 image with uv and iputils. The monitoring scripts are mounted
# at runtime to allow iterating without rebuilding the image.
# ==============================================================================

FROM python:3.14-slim-bookworm

# Install uv from the official Astral image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# iputils provides the ping binary required by the probe engine.
RUN apt-get update \
    && apt-get install -y --no-install-recommends iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first for better layer caching.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Keep the container alive; commands are executed with `docker compose exec`.
CMD ["sleep", "infinity"]
