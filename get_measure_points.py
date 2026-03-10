import os
import django
import logging
import requests
import json

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.services.deye_service import DeyeService

def get_measure_points():
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

    print(f"Checking measure points list for device: {device_sn}")
    
    # Try different potential endpoints for measure point list
    endpoints = [
        f"/v1.0/device/measurePointList",
        f"/v1.0/device/measurePoints",
        f"/v1.0/config/measurePoints"
    ]
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    for ep in endpoints:
        url = f"{service.base_url}{ep}"
        print(f"\nTrying endpoint: {url}")
        try:
            # Try both GET and POST
            params = {"appId": service.app_id, "deviceSn": device_sn}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            print(f"GET Status: {response.status_code}")
            if response.status_code == 200:
                print(json.dumps(response.json(), indent=2))
                continue
                
            response = requests.post(url, params={"appId": service.app_id}, json={"deviceSn": device_sn}, headers=headers, timeout=10)
            print(f"POST Status: {response.status_code}")
            if response.status_code == 200:
                print(json.dumps(response.json(), indent=2))
        except Exception as e:
            print(f"Error for {url}: {e}")

if __name__ == "__main__":
    get_measure_points()
