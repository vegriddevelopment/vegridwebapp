import os
import sys
import django
import json
import requests

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.services.deye_service import DeyeService

def list_api_devices():
    service = DeyeService()
    print("--- Deye API Station/Device List ---")
    
    stations_resp = service.get_station_list_with_device()
    if stations_resp.get('code') in [0, "0", "1000000"]:
        data = stations_resp.get('data', {})
        stations = data.get('list', []) or stations_resp.get('stationList', [])
        
        print(f"Found {len(stations)} stations.")
        for s in stations:
            print(f"\nStation: {s.get('name')} (ID: {s.get('id')})")
            devices = s.get('deviceListItems', [])
            for d in devices:
                print(f"  - Device: {d.get('name')} (SN: {d.get('deviceSn')}, Type: {d.get('deviceType')})")
    else:
        print(f"FAILED: {stations_resp}")

if __name__ == "__main__":
    list_api_devices()
