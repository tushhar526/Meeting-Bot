#!/bin/bash

set -e
export USER_ID=$(id -u)
export XDG_RUNTIME_DIR=/var/run/user/$USER_ID
export PULSE_SERVER=unix:/var/run/user/$USER_ID/pulse/native

mkdir -p $XDG_RUNTIME_DIR/pulse
chmod 700 $XDG_RUNTIME_DIR
chmod 700 $XDG_RUNTIME_DIR/pulse

echo "Starting pulse audio daemon"
pulseaudio --daemonize=yes \
           --system=no \
           --exit-idle-time=-1 \
           --log-target=stderr \
           --load="module-native-protocol-unix" \
           --load="module-native-protocol-tcp listen=127.0.0.1"

sleep 2

pactl info || echo "Pulse audio is not running"

echo "Starting redis server"
redis-server  --logfile "" &
REDIS_PID=$!

sleep 3

redis-cli ping || echo "Redis is not working"

echo "Starting celery worker"
celery -A app.celery_app:celery_app worker --concurrency=4 --loglevel=info &
CELERY_PID=$!

echo "Starting the bot app"
python -m uvicorn app.main:create_app --host 0.0.0.0 --port 5000

trap "kill $CELERY_PID $REDIS_PID 2>/dev/null || True" EXIT
