#!/bin/bash
# Start Celery worker in the background
celery -A core worker --loglevel=info &

# Start Gunicorn (foreground — keeps container alive)
gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 2
