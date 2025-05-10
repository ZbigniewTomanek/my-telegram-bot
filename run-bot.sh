#!/bin/bash

docker rm -f telegram_bot 2>/dev/null || true
docker run --rm \
  -v "$(pwd):/app" \
  -w /app \
  --rm \
  --env-file .env \
  -v "$(uv cache dir):/uv-cache" \
  -u "$(id -u):$(id -g)" \
  -e PYTHONPATH=/app \
  --name telegram_bot \
  ghcr.io/astral-sh/uv:python3.13-alpine \
  uv run --cache-dir /uv-cache --isolated telegram_bot/main.py
