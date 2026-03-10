import os
import sys
import django
import requests
import json

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.services.deye_service import DeyeService

def test_monthly_device_history():
    service = DeyeService()
    device_sn = "2510171733"
    token = service.get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    url = f"{service.base_url}/v1.0/device/history"
    
    # Requesting data for 2026-01 to 2026-03
    payload = {
        "deviceSn": device_sn,
        "granularity": 3, # Month
        "startAt": "2026-01",
        "endAt": "2026-03",
        "measurePoints": None
    }
    
    print(f"Requesting monthly device history for {device_sn}...")
    resp = requests.post(url, params={"appId": service.app_id}, json=payload, headers=headers)
    data = resp.json()
    
    if data.get('code') in [0, "0", "1000000"]:
        print("SUCCESS (Device):")
        items = data.get('dataList', [])
        for i in items:
            print(json.dumps(i, indent=2))
    else:
        msg = str(data).encode('ascii', 'ignore').decode('ascii')
        print(f"FAILED (Device): {msg}")

    # Also try Station History
    url_station = f"{service.base_url}/v1.0/station/history"
    payload_station = {
        "stationId": "61776373",
        "granularity": 3,
        "startAt": "2026-01",
        "endAt": "2026-03"
    }
    print(f"\nRequesting monthly station history for 61776373...")
    resp_s = requests.post(url_station, params={"appId": service.app_id}, json=payload_station, headers=headers)
    data_s = resp_s.json()
    if data_s.get('code') in [0, "0", "1000000"]:
        print("SUCCESS (Station):")
        items = data_s.get('data', {}).get('items', []) or data_s.get('dataList', [])
        for i in items:
            print(json.dumps(i, indent=2))
    else:
        print(f"FAILED (Station): {data_s}")

if __name__ == "__main__":
    test_monthly_device_history()
