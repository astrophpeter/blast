#!/bin/env bash

bash entrypoints/wait-for-it.sh database:3306 --timeout=0 &&
bash entrypoints/wait-for-it.sh nginx:80 --timeout=0 &&
python manage.py makemigrations &&
python manage.py migrate &&
gunicorn app.wsgi:application --bind 0.0.0.0:8000
