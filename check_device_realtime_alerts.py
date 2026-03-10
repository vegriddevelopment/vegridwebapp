#!/usr/bin/env python3
"""
Check if device realtime data contains any alert or warning information
"""

import os
import sys
import requests
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
import django
django.setup()

from vegrid_app.services.deye_service import DeyeService
from vegrid_app.deye_api import DeyeAPI

def check_device_realtime_alerts():
    """Check if device realtime data has alert information"""
    
    print("Checking device realtime data for alerts/warnings...")
    
    # First, get a device SN
    service = DeyeService()
    devices_response = service.get_station_list_with_device()
    
    if devices_response.get('code') in [0, "0", "1000000"]:
        station_list = devices_response.get('stationList', devices_response.get('data', {}).get('list', []))
        if station_list:
            first_station = station_list[0]
            device_list_items = first_station.get('deviceListItems', [])
            if device_list_items:
                device_sn = device_list_items[0].get('deviceSn')
                print(f"Using device: {device_sn} ({first_station.get('name')})")
                
                # Get realtime data
                api = DeyeAPI()
                token = service.get_token()
                
                realtime_response = api.get_device_realtime(token, device_sn)
                
                print("\nDevice Realtime Data:")
                print(json.dumps(realtime_response, indent=2))
                
                # Check if there's any alert/warning information
                if 'data' in realtime_response:
                    data = realtime_response['data']
                    for key, value in data.items():
                        if 'alert' in key.lower() or 'warning' in key.lower() or 'fault' in key.lower():
                            print(f"\nFound alert-related field: {key} = {value}")
                
                return
                
    print("No devices found")


if __name__ == "__main__":
    check_device_realtime_alerts()
