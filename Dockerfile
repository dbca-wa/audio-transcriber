# syntax=docker/dockerfile:1
# Prepare the base environment.
FROM python:3.13-slim-bookworm AS builder_base

ENV UV_LINK_MODE=copy \
  UV_COMPILE_BYTECODE=1 \
  UV_PYTHON_DOWNLOADS=never \
  UV_PROJECT_ENVIRONMENT=/app/.venv

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/
COPY pyproject.toml uv.lock /_lock/
# This layer is cached until uv.lock or pyproject.toml change.
RUN --mount=type=cache,target=/root/.cache \
  cd /_lock && \
  uv sync --frozen

##################################################################################

FROM python:3.13-slim-bookworm
LABEL org.opencontainers.image.authors=ashley@ropable.com
LABEL org.opencontainers.image.source=https://github.com/dbca-wa/audio-transcriber

# Install required OS packages.
RUN apt-get update -y \
  && apt-get upgrade -y \
  && apt-get install -y --no-install-recommends ffmpeg \
  # && apt-get install -y wget libmagic-dev gcc binutils python3-dev ffmpeg lsb-release software-properties-common gnupg \
  && rm -rf /var/lib/apt/lists/*

# We have to install LLVM 15, as this is what llvmlite builds against at present.
# RUN wget https://apt.llvm.org/llvm.sh \
#   && chmod +x llvm.sh \
#   && ./llvm.sh 15
# ENV LLVM_CONFIG=/usr/bin/llvm-config-15
# RUN rm -rf /var/lib/apt/lists/*

# Create a non-root user.
RUN groupadd -r -g 1000 app \
  && useradd -r -u 1000 -d /app -g app -N app

COPY --from=builder_base --chown=app:app /app /app
# Make sure we use the virtualenv by default.
# Run Python unbuffered.
ENV PATH=/app/.venv/bin:$PATH PYTHONUNBUFFERED=1

# Install the project.
WORKDIR /app
COPY pyproject.toml transcriber.py ./
USER app
