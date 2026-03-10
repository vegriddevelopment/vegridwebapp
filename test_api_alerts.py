import os
import django
import requests
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from django.contrib.auth import authenticate, login
from django.test import Client

def test_api_alerts():
    """Test the api_alerts endpoint"""
    
    client = Client()
    
    # Authenticate user (we need to know the credentials)
    # Let's try to use the test user
    username = "testuser"
    password = "testpassword"
    
    try:
        login_response = client.post('/api/verify-login-otp/', json={
            'phone_number': '+254712345678',
            'otp': '123456'
        }, content_type='application/json')
        print("Login response status:", login_response.status_code)
        print("Login response content:", login_response.content)
        
        # Now fetch alerts
        alerts_response = client.get('/api/alerts/')
        print("Alerts response status:", alerts_response.status_code)
        print("Alerts response content:", alerts_response.json())
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    test_api_alerts()
