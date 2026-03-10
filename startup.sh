#!/bin/bash

# VeGrid Django Application Startup Script
# This script is used to start the Django application with Gunicorn

# Set environment variables
export DJANGO_SETTINGS_MODULE="vegrid_project.settings"
export PYTHONPATH=$(pwd)

# Activate virtual environment if exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "env/bin/activate" ]; then
    source env/bin/activate
fi

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Apply migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# Start Gunicorn server
echo "Starting Gunicorn server..."
gunicorn vegrid_project.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 300
