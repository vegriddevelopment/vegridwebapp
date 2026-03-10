#!/usr/bin/env python3
"""
Script to fix the JavaScript error in index.html
"""

import os

def main():
    file_path = 'templates/index.html'
    
    if not os.path.exists(file_path):
        print("Error: index.html not found")
        return False
    
    print("Reading index.html...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find and replace the problematic code
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
        print("Found problematic code")
        content = content.replace(old_code, new_code)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("JavaScript error fixed")
        return True
    else:
        print("Could not find the problematic code")
        return False

if __name__ == "__main__":
    success = main()
    import sys
    sys.exit(0 if success else 1)
