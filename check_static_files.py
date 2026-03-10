#!/usr/bin/env python3
"""
Script to check and fix static files configuration in Django project
"""

import os
import sys
import shutil
import subprocess

def fix_javascript_error():
    """Fix the JavaScript error in index.html"""
    file_path = 'templates/index.html'
    
    if not os.path.exists(file_path):
        print("Error: index.html not found")
        return False
    
    print("Fixing JavaScript error...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    old_code = """            // Contact form submission
            document.getElementById('contactForm').addEventListener('submit', function(e) {
                e.preventDefault();
                alert('Thank you for your message! We will get back to you soon.');
                this.reset();
            });"""
    
    new_code = """            // Contact form submission
            const contactForm = document.getElementById('contactForm');
            if (contactForm) {
                contactForm.addEventListener('submit', function(e) {
                    e.preventDefault();
                    alert('Thank you for your message! We will get back to you soon.');
                    this.reset();
                });
            }"""
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("JavaScript error fixed")
        return True
    else:
        print("JavaScript error already fixed")
        return True

def main():
    # Check if we're in the right directory
    if not os.path.exists('manage.py'):
        print("Error: manage.py not found. Please run this script from the Django project root directory.")
        return False

    # Fix JavaScript error first
    fix_javascript_error()

    # Define directories
    project_root = os.getcwd()
    static_dir = os.path.join(project_root, 'static')
    assets_dir = os.path.join(project_root, 'assets')
    css_dir = os.path.join(project_root, 'css')
    js_dir = os.path.join(project_root, 'js')

    print("\nChecking static files configuration...")
    
    # Check if source directories exist
    sources_exist = all(os.path.exists(d) for d in [assets_dir, css_dir, js_dir])
    if not sources_exist:
        print("Error: Required source directories (assets, css, js) not found")
        return False

    print("Source directories found")

    # Check if collectstatic needs to be run
    needs_collection = False
    
    if not os.path.exists(static_dir):
        print("Static directory does not exist - will create it")
        needs_collection = True
    else:
        # Check if static directory is empty or outdated
        static_files_count = sum(len(files) for _, _, files in os.walk(static_dir))
        if static_files_count == 0:
            print("Static directory is empty - needs collection")
            needs_collection = True

    # Run collectstatic if needed
    if needs_collection:
        print("Running collectstatic...")
        try:
            result = subprocess.run(
                [sys.executable, 'manage.py', 'collectstatic', '--noinput'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"Collectstatic completed successfully: {result.stdout.strip()}")
            else:
                print(f"Collectstatic failed: {result.stderr.strip()}")
                return False
        except Exception as e:
            print(f"Error running collectstatic: {e}")
            return False
    else:
        print("Static files already collected")

    # Verify collected files structure
    print("\nVerifying static files structure...")
    static_checks = [
        ('', 'styles.css'),
        ('', 'scripts.js'),
        ('', 'vegrid-logo-BBC4G70n.png'),
        ('img', 'Image_fx.png'),
        ('img/herosection', 'hero-home.jpg'),
        ('img/home use', 'Image_fx.png'),
        ('img/home use', 'Image_fx (17).png'),
        ('img/commercial', 'Image_fx (1).png'),
        ('img/industrial', 'Image_fx.png'),
        ('img/industrial', 'Image_fx (20).png'),
        ('img/agriculture', 'Image_fx.png'),
        ('img/agriculture', 'Image_fx (1).png'),
        ('img/our story', 'Image_fx (18).png'),
        ('img/our story', 'Image_fx (19).png'),
        ('img/our story', 'Image_fx (20).png'),
        ('img/our story', 'Image_fx (21).png'),
        ('img/our story', 'Image_fx (22).png'),
        ('img/About us', 'Image_fx (17).png'),
        ('img/About us', 'Image_fx (18).png'),
        ('img/About us', 'Image_fx (19).png')
    ]

    missing_files = []
    for dir_name, file_name in static_checks:
        file_path = os.path.join(static_dir, dir_name, file_name)
        if os.path.exists(file_path):
            print(f"✅ {os.path.join(dir_name, file_name)}")
        else:
            print(f"❌ {os.path.join(dir_name, file_name)}")
            missing_files.append(os.path.join(dir_name, file_name))

    if missing_files:
        print(f"\nError: {len(missing_files)} static files are missing")
        return False
    else:
        print("\nAll required static files are present")

    # Check permissions
    print("\nChecking static files permissions...")
    try:
        # Make sure static directory is readable
        os.chmod(static_dir, 0o755)
        
        # Recursively set permissions
        for root, dirs, files in os.walk(static_dir):
            for d in dirs:
                os.chmod(os.path.join(root, d), 0o755)
            for f in files:
                os.chmod(os.path.join(root, f), 0o644)
        
        print("Permissions set correctly")
    except Exception as e:
        print(f"Warning: Could not set permissions: {e}")

    print("\nStatic files configuration check completed successfully!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
