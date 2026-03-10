#!/bin/bash
"""
Deployment script to fix static files and JavaScript error on cPanel
"""

echo "=== VeGrid Static Files Deployment Script ==="
echo ""

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "ERROR: manage.py not found. Please run this script from the Django project root directory."
    exit 1
fi

# Fix JavaScript error
echo "1. Fixing JavaScript error..."
python fix_javascript_error.py

# Collect static files
echo ""
echo "2. Collecting static files..."
python manage.py collectstatic --noinput

# Check static files configuration
echo ""
echo "3. Verifying static files configuration..."
python check_static_files.py

echo ""
echo "=== Deployment Completed ==="
echo "Static files should now be properly collected and accessible from /static/ URL."
