#!/bin/env bash
bash entrypoints/wait-for-it.sh ${DATABASE_HOST}:${DATABASE_PORT} --timeout=0 &&
bash entrypoints/wait-for-it.sh ${WEB_SERVER_HOST}:${WEB_SERVER_PORT} --timeout=0 &&
python manage.py makemigrations &&
python manage.py migrate &&
python manage.py createsuperuser --noinput &&
python manage.py collectstatic &&
bash entrypoints/load_initial_data.sh &&
./manage.py shell < entrypoints/setup_initial_periodic_tasks.py &&
bash entrypoints/load_example_data.sh &&
gunicorn app.wsgi:application --bind 0.0.0.0:${WEB_APP_PORT}
