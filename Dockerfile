FROM python:3.13-slim

# Create app directory
WORKDIR /app

# Make apt non-interactive to avoid blocking during cloud builds
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies required by some Python packages
RUN apt-get update \
    && apt-get install -yq --no-install-recommends build-essential git curl \
    && rm -rf /var/lib/apt/lists/*

# install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-cache --no-dev
# Copy the full repository into the image so pip can build the package
COPY . /app/

# Create a persistent data directory; run DB seeding at container startup (not at build)
RUN mkdir -p /data

# Expose the default ADK port
EXPOSE 8000

# Copy an entrypoint that seeds DB at runtime and starts the server
COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
# Default command: start the ADK web dev UI (entrypoint will run seeding first)
CMD ["/bin/sh", "-lc", "uv run uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
