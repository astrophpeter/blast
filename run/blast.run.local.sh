#!/bin/env bash
bash app/entrypoints/clean_data.sh
docker compose -f docker/docker-compose.yml --env-file env/.env.dev up --build
