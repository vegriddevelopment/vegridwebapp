#!/usr/bin/env python3
"""
Test script to check if Deye Cloud API has an alerts endpoint.
This will help us understand how to fetch alerts from Deye Cloud.
"""

import os
import sys
import requests
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
import django
django.setup()

from vegrid_app.services.deye_service import DeyeService

def test_deye_alerts_endpoints():
    """Test various possible alerts endpoints in Deye Cloud API"""
    
    service = DeyeService()
    token = service.get_token()
    base_url = service.base_url
    app_id = service.app_id
    
    print("Testing Deye Cloud API for alerts endpoints...")
    print(f"Base URL: {base_url}")
    print(f"Token obtained: {token[:10]}...")
    
    # Common headers for API requests
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test possible alerts endpoints
    possible_endpoints = [
        "/v1.0/device/alerts",
        "/v1.0/station/alerts",
        "/v1.0/device/alert",
        "/v1.0/station/alert",
        "/v1.0/alerts",
        "/v1.0/alert",
        "/v1.0/device/warning",
        "/v1.0/station/warning",
        "/v1.0/warning",
        "/v1.0/device/notification",
        "/v1.0/station/notification",
        "/v1.0/notification"
    ]
    
    # Get devices list first to use deviceSn
    devices_response = service.get_station_list_with_device()
    device_sn = None
    
    if devices_response.get('code') in [0, "0", "1000000"]:
        station_list = devices_response.get('stationList', devices_response.get('data', {}).get('list', []))
        if station_list:
            first_station = station_list[0]
            device_list_items = first_station.get('deviceListItems', [])
            if device_list_items:
                device_sn = device_list_items[0].get('deviceSn')
                print(f"Found test device: {device_sn}")
    
    # Test each endpoint with different HTTP methods
    for endpoint in possible_endpoints:
        url = f"{base_url}{endpoint}"
        print(f"\nTesting: {endpoint}")
        
        # Try GET method
        try:
            response = requests.get(url, params={"appId": app_id}, headers=headers, timeout=10)
            print(f"GET: Status {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Success: {json.dumps(data, indent=2)}")
        except Exception as e:
            print(f"GET Error: {str(e)}")
        
        # Try POST method with possible payload
        try:
            payload = {}
            if device_sn:
                payload["deviceSn"] = device_sn
                
            response = requests.post(url, params={"appId": app_id}, json=payload, headers=headers, timeout=10)
            print(f"POST: Status {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Success: {json.dumps(data, indent=2)}")
        except Exception as e:
            print(f"POST Error: {str(e)}")
            
    print("\nTesting completed!")


if __name__ == "__main__":
    test_deye_alerts_endpoints()
