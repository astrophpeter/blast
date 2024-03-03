#!/bin/env bash
bash entrypoints/wait-for-it.sh ${DATABASE_HOST}:${DATABASE_PORT} --timeout=0 &&
bash entrypoints/wait-for-it.sh ${MESSAGE_BROKER_HOST}:${MESSAGE_BROKER_PORT} --timeout=0 &&
bash entrypoints/wait-for-it.sh ${WEB_APP_HOST}:${WEB_APP_PORT} --timeout=0 &&
python manage.py shell < entrypoints/initialize_dustmaps.py &&
celery -A app worker -l ERROR --max-memory-per-child 12000
