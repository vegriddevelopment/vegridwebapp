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

def test_granularity_2():
    service = DeyeService()
    device_sn = "2510171733"
    token = service.get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    url = f"{service.base_url}/v1.0/device/history"
    
    payload = {
        "deviceSn": device_sn,
        "granularity": 2, 
        "startAt": "2026-03-01",
        "endAt": "2026-03-31",
        "measurePoints": None
    }
    
    print(f"Requesting device history for March 2026 with granularity=2...")
    resp = requests.post(url, params={"appId": service.app_id}, json=payload, headers=headers)
    data = resp.json()
    
    if data.get('code') in [0, "0", "1000000"]:
        print("SUCCESS:")
        items = data.get('dataList', [])
        for i in items:
             print(json.dumps(i, indent=2))
    else:
        print(f"FAILED with code: {data.get('code')}")

if __name__ == "__main__":
    test_granularity_2()
