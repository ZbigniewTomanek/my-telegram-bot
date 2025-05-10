#!/bin/bash

docker rm -f telegram_bot 2>/dev/null || true
docker run --rm \
  -v "$(pwd):/app" \
  -w /app \
  --rm \
  --env-file .env \
  -v "$(pwd)/.cache:/cache" \
  -u "$(id -u):$(id -g)" \
  -e PYTHONPATH=/app \
  --name telegram_bot \
  ghcr.io/astral-sh/uv:python3.13-bookworm \
  uv run --cache-dir /cache --isolated telegram_bot/main.py
