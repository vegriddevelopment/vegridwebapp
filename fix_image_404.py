#!/usr/bin/env python3
"""
Script to fix image 404 errors in Django project
"""

import os
import sys
import subprocess
import urllib.parse
from pathlib import Path

def find_missing_images():
    """Find which images are missing in static directory"""
    
    static_img_dir = Path("static/img")
    if not static_img_dir.exists():
        print("Static img directory not found")
        return []
    
    # All required images from 404 errors
    required_images = [
        "Image_fx (1).png",
        "Image_fx (20).png", 
        "Image_fx.png",
        "Image_fx (17).png"
    ]
    
    missing = []
    
    for img in required_images:
        found = False
        
        # Search for the image in all subdirectories
        for root, dirs, files in os.walk(static_img_dir):
            if img in files:
                print(f"✓ {img} found in {root}")
                found = True
        
        if not found:
            print(f"✗ {img} not found in static/img directory")
            missing.append(img)
    
    return missing

def verify_collectstatic():
    """Verify collectstatic has been run correctly"""
    
    static_dir = Path("static")
    
    if not static_dir.exists() or not any(static_dir.iterdir()):
        print("Static directory not found or empty. Running collectstatic...")
        try:
            result = subprocess.run(
                [sys.executable, "manage.py", "collectstatic", "--noinput"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"collectstatic completed: {result.stdout.strip()}")
            else:
                print(f"collectstatic failed: {result.stderr.strip()}")
                return False
        except Exception as e:
            print(f"Error running collectstatic: {e}")
            return False
    else:
        print("Static directory exists and is not empty")
    
    return True

def check_static_files_config():
    """Check if static files are configured correctly in settings.py"""
    
    settings_file = Path("vegrid_project/settings.py")
    
    if not settings_file.exists():
        print("settings.py not found")
        return False
    
    with open(settings_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Check if required settings are present (with flexible matching)
    has_static_url = "STATIC_URL" in content and "/static/" in content
    has_static_root = "STATIC_ROOT" in content and "static" in content
    has_static_dirs = "STATICFILES_DIRS" in content
    
    if has_static_url and has_static_root and has_static_dirs:
        print("OK - Static files configuration is correct")
        return True
    else:
        print("ERROR - Static files configuration is missing required settings")
        return False

def check_url_config():
    """Check if static files are properly configured in urls.py"""
    
    urls_file = Path("vegrid_project/urls.py")
    
    if not urls_file.exists():
        print("urls.py not found")
        return False
    
    with open(urls_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    static_url_config = [
        "from django.conf.urls.static import static",
        "from django.conf import settings",
        "urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)"
    ]
    
    all_configured = True
    for config in static_url_config:
        if config not in content:
            print(f"✗ Missing static URL configuration: {config}")
            all_configured = False
    
    if all_configured:
        print("✓ Static URL configuration is correct")
    
    return all_configured

def main():
    print("=== Fixing Image 404 Errors ===")
    
    # Step 1: Check and run collectstatic
    if not verify_collectstatic():
        return False
    
    # Step 2: Check static files configuration
    if not check_static_files_config():
        return False
    
    # Step 3: Check URL configuration
    if not check_url_config():
        return False
    
    # Step 4: Find missing images
    missing_images = find_missing_images()
    
    if missing_images:
        print(f"\nError: {len(missing_images)} images are missing from static directory")
        return False
    
    print("\n✅ All images are properly collected and configured!")
    
    print("\n=== Common Causes of 404 Errors ===")
    print("1. Static files not collected on server - run 'python manage.py collectstatic --noinput'")
    print("2. Incorrect static URL configuration in settings.py or urls.py")
    print("3. Browser cache - try hard refresh (Ctrl+F5)")
    print("4. Permissions issues - ensure static directory has readable permissions")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
