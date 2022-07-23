#!/bin/env bash
bash entrypoints/wait-for-it.sh ${DATABASE_HOST}:${DATABASE_PORT} --timeout=0 &&
python manage.py makemigrations &&
python manage.py migrate &&
python manage.py test host.tests -v 2
