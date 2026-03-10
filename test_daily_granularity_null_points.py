import os
import sys
import django
import requests
import json
from datetime import datetime

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.services.deye_service import DeyeService

def test_daily_granularity_null_points():
    service = DeyeService()
    device_sn = "2510171733"
    token = service.get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    url = f"{service.base_url}/v1.0/device/history"
    
    # Requesting daily data for March 2026 with NULL measurePoints
    payload = {
        "deviceSn": device_sn,
        "granularity": 1, # Day
        "startAt": "2026-03-01",
        "endAt": "2026-03-31",
        "measurePoints": None
    }
    
    print(f"Requesting daily device history for March 2026 with measurePoints=None...")
    resp = requests.post(url, params={"appId": service.app_id}, json=payload, headers=headers)
    data = resp.json()
    
    if data.get('code') in [0, "0", "1000000"]:
        print("SUCCESS:")
        # ... (rest of the code)
    else:
        print(f"FAILED with code: {data.get('code')} and msg: {data.get('msg', 'no message')}")

if __name__ == "__main__":
    test_daily_granularity_null_points()
