#!/bin/bash

MAX_WORKERS=$(printf "%.0f" $(expr "$(nproc)" "/" 4 | bc))
MAX_THREADS=$(printf "%.0f" $(expr "$(nproc)" "/" 2 | bc))

exec gunicorn iamksm_bot.app.webhook:FLASK_APP \
    -b 0.0.0.0:7777 \
    -k gevent \
    --threads $MAX_THREADS
