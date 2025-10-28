FROM python:3.13-slim

# Create app directory
WORKDIR /app

# Make apt non-interactive to avoid blocking during cloud builds
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies required by some Python packages
RUN apt-get update \
    && apt-get install -yq --no-install-recommends build-essential git curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the full repository into the image so pip can build the package
COPY . /app/

# Use pip to install the project dependencies (adk) from pyproject
# Generate a temporary requirements file from pyproject.toml in a portable way
# Use --no-cache-dir to reduce image size and be explicit about upgrades
RUN pip install --no-cache-dir -U pip setuptools wheel \
    && python - <<'PY'
import tomllib
data = tomllib.loads(open('pyproject.toml','r',encoding='utf-8').read())
deps = data.get('project',{}).get('dependencies',[])
open('requirements-build.txt','w').write('\n'.join(deps))
PY

RUN if [ -s requirements-build.txt ]; then pip install --no-cache-dir -r requirements-build.txt; fi \
    && pip install --no-cache-dir -e . \
    && rm -f requirements-build.txt

# Create a persistent data directory; run DB seeding at container startup (not at build)
RUN mkdir -p /data

# Expose the default ADK port
EXPOSE 8000

# Copy an entrypoint that seeds DB at runtime and starts the server
COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
# Default command: start the ADK web dev UI (entrypoint will run seeding first)
CMD ["adk", "web", "src/hd_google_hackathon/agents", "--host", "0.0.0.0", "--port", "8000"]
