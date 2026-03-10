#!/usr/bin/env python3
"""
Check if device history contains any alert or warning information
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
from vegrid_app.deye_api import DeyeAPI

def check_device_history_alerts():
    """Check if device history data has alert information"""
    
    print("Checking device history data for alerts/warnings...")
    
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
                
                # Get device history data for various measure points
                token = service.get_token()
                api = DeyeAPI()
                
                # Check if there's any alert measure points
                # Common alert-related measure points might include:
                # - DeviceFault
                # - SystemAlarm
                # - Warning
                # - Error
                # - Status
                
                # Get device history for possible alert measure points
                base_url = service.base_url
                app_id = service.app_id
                
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
                
                # Try to get device history with possible alert measure points
                history_url = f"{base_url}/v1.0/device/history"
                
                # Try different possible alert measure points
                possible_alert_points = [
                    "DeviceFault", 
                    "SystemAlarm", 
                    "Warning", 
                    "Error", 
                    "Status",
                    "FaultCode",
                    "AlarmCode"
                ]
                
                for measure_point in possible_alert_points:
                    print(f"\nTrying measure point: {measure_point}")
                    
                    try:
                        payload = {
                            "deviceSn": device_sn,
                            "measurePoints": [measure_point],
                            "startAt": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
                            "endAt": datetime.now().strftime("%Y-%m-%d"),
                            "granularity": 1
                        }
                        
                        params = {"appId": app_id}
                        response = requests.post(history_url, params=params, json=payload, headers=headers, timeout=10)
                        
                        if response.status_code == 200:
                            data = response.json()
                            print(f"Success: {json.dumps(data, indent=2)}")
                            
                            # Check if there's any data
                            if 'dataList' in data and data['dataList']:
                                print(f"Found {len(data['dataList'])} data points")
                            
                        else:
                            print(f"Error: Status code {response.status_code}")
                            print(response.text)
                            
                    except Exception as e:
                        print(f"Error: {str(e)}")
                
                return
                
    print("No devices found")


if __name__ == "__main__":
    check_device_history_alerts()
