#!/bin/bash

set -e

# mkdir -p /var/run/user/1000/pulse
# chown -R audiobot:audiobot /var/run/user/1000/pulse

chmod 700 /var/run/user/1000/pulse

echo "Starting pulse audio daemon"
pulseaudio --daemonize=yes \
           --system=no \
           --exit-idle-time=-1 \
           --log-target=stderr \
           --load="module-native-protocol-unix" \
           --load="module-native-protocol-tcp listen=127.0.0.1" \
           --load="module-null-sink" 2>&1 || echo "Pulse audio already running or error (continuing)"

sleep 2

pactl info || echo "Pulse audio is not running"

echo "Starting redis server"
redis-server  --logfile "" &
REDIS_PID=$!

sleep 3

redis-cli ping || echo "Redis is not working"

echo "Starting celery worker"
celery -A app.celery_app:celery worker --pool=solo --loglevel=info &
CELERY_PID=$!

echo "Starting the bot app"
python run.py

trap "kill $CELERY_PID $REDIS_PID 2>/dev/null || True" EXIT
