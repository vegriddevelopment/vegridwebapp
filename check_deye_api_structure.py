#!/usr/bin/env python3
"""
Check Deye API structure to understand available endpoints
"""

import os
import sys
import json
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
import django
django.setup()

from vegrid_app.services.deye_service import DeyeService
from vegrid_app.deye_api import DeyeAPI

def check_api_endpoints():
    """Check what Deye Cloud API endpoints are available"""
    
    print("Checking Deye Cloud API endpoints...")
    
    # Get token and basic info
    service = DeyeService()
    token = service.get_token()
    api = DeyeAPI()
    
    print(f"Token: {token[:10]}...")
    print(f"Base URL: {service.base_url}")
    
    # Check what's available in station detail
    station_list_response = service.get_station_list_with_device()
    print("\nStation List Response:")
    print(json.dumps(station_list_response, indent=2))
    
    # Check if there's any alert/warning information in station list
    if station_list_response.get('code') in [0, "0", "1000000"]:
        station_list = station_list_response.get('stationList', station_list_response.get('data', {}).get('list', []))
        if station_list:
            first_station = station_list[0]
            print(f"\nFirst Station: {first_station.get('name')}")
            
            # Check fields for alert/warning information
            for key, value in first_station.items():
                if 'alert' in key.lower() or 'warning' in key.lower() or 'fault' in key.lower() or 'status' in key.lower():
                    print(f"  {key}: {value}")


if __name__ == "__main__":
    check_api_endpoints()
