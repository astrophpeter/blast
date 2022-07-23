#!/bin/env bash
bash entrypoints/wait-for-it.sh ${DATABASE_HOST}:${DATABASE_PORT} --timeout=0 &&
bash entrypoints/wait-for-it.sh ${MESSAGE_BROKER_PORT}:${MESSAGE_BROKER_PORT} --timeout=0 &&
bash entrypoints/wait-for-it.sh ${WEB_APP_HOST}:${WEB_APP_PORT} --timeout=0 &&
celery --broker=amqp://guest:guest@rabbitmq:${MESSAGE_BROKER_PORT}// flower --port=${FLOWER_PORT}
