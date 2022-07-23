#!/bin/env bash
source env/.env.dev
bash app/entrypoints/clean_data.sh
docker compose -f docker/docker-compose.test.yml --env-file env/.env.dev up --exit-code-from app
