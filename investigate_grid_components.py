import os
import django
import logging
import requests
import json
from datetime import datetime, timedelta

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.services.deye_service import DeyeService

def investigate_grid():
    service = DeyeService()
    token = service.get_token()
    
    # Get a real device SN
    stations_resp = service.get_station_list_with_device()
    device_sn = None
    if stations_resp.get('code') in [0, "0", "1000000"]:
        station_list = stations_resp.get('stationList', stations_resp.get('data', {}).get('list', []))
        for station in station_list:
            if station.get('deviceListItems'):
                device_sn = station.get('deviceListItems')[0].get('deviceSn')
                break
    
    if not device_sn:
        print("No device found")
        return

    print(f"Investigating grid components for device: {device_sn}")
    
    grid_points = [
        "TotalGridPower",
        "ExternalCT1Power", "ExternalCT2Power", "ExternalCT3Power",
        "TotalExternalCTPower", "InternalCT1Power", "InternalCT2Power", "InternalCT3Power",
        "GridPowerL1", "GridPowerL2", "GridPowerL3"
    ]
    
    url = f"{service.base_url}/v1.0/device/history"
    params = {"appId": service.app_id}
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Check last 24 hours
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)
    
    # Try points one by one to find which ones are valid
    valid_points = []
    for point in grid_points:
        payload = {
            "deviceSn": device_sn,
            "measurePoints": [point],
            "startAt": start_date.strftime("%Y-%m-%d"),
            "endAt": end_date.strftime("%Y-%m-%d"),
            "granularity": 1
        }
        
        try:
            response = requests.post(url, params=params, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('code') in [0, "0", "1000000"]:
                    data_list = result.get('dataList', [])
                    if data_list:
                        # Check if it has value
                        has_data = False
                        for p in reversed(data_list):
                            if p.get('itemList'):
                                item = p['itemList'][0]
                                print(f"VALID: {point} = {item.get('value')} {item.get('unit', '')}")
                                valid_points.append(point)
                                has_data = True
                                break
                        if not has_data:
                            print(f"VALID (but no data): {point}")
                    else:
                        print(f"VALID (but empty list): {point}")
                # else: ignore invalid points
            else:
                print(f"HTTP Error for {point}: {response.status_code}")
        except Exception as e:
            print(f"Error for {point}: {e}")
    
    print(f"\nSummary of valid points: {valid_points}")

if __name__ == "__main__":
    investigate_grid()
