#!/bin/sh

set -eu

exec gunicorn app.main:app \
  --chdir /app/api \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --access-logfile - \
  --error-logfile -
