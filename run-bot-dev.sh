#!/bin/bash

docker run -it --rm \
  -v "$(pwd):/app" \
  -w /app \
  --rm \
  --env-file .env \
  -e PYTHONPATH=/app \
  --name telegram_bot \
  ghcr.io/astral-sh/uv:python3.13-alpine \
  uv run --isolated telegram_bot/main.py
