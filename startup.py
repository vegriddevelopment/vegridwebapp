#!/usr/bin/env python
"""
VeGrid Django Application Startup Script
This script is used to start the Django application with Gunicorn
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Main startup function"""
    # Get project root directory
    project_root = Path(__file__).resolve().parent
    
    # Set environment variables
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
    os.environ.setdefault('PYTHONPATH', str(project_root))
    
    # Change to project root directory
    os.chdir(str(project_root))
    
    print("Starting VeGrid Django application...")
    
    try:
        # Collect static files
        print("\n1. Collecting static files...")
        subprocess.run([sys.executable, 'manage.py', 'collectstatic', '--noinput'], check=True)
        
        # Apply migrations
        print("\n2. Applying database migrations...")
        subprocess.run([sys.executable, 'manage.py', 'migrate', '--noinput'], check=True)
        
        # Start Gunicorn server
        print("\n3. Starting Gunicorn server...")
        print("Server will be available at http://0.0.0.0:8000")
        subprocess.run([
            sys.executable, '-m', 'gunicorn', 
            'vegrid_project.wsgi:application', 
            '--bind', '0.0.0.0:8000',
            '--workers', '4',
            '--timeout', '300'
        ], check=True)
        
    except subprocess.CalledProcessError as e:
        print(f"\nError: Command failed with code {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
