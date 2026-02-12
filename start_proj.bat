@echo off

echo Starting Flask Server
start cmd /k python run.py

echo Starting the worker
start cmd /k celery -A app.celery_app:celery worker --pool=solo --loglevel=info
