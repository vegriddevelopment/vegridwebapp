import os
import sys
import django
import json
import requests
from datetime import datetime, timedelta

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.services.deye_service import DeyeService

def test_granularity():
    service = DeyeService()
    target_sn = "2510171733"
    token = service.get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    url = f"{service.base_url}/v1.0/device/history"
    
    # Test February 2026
    start_at = "2026-02-01"
    end_at = "2026-02-28"
    
    measure_points = ["DailyActiveProduction", "DailyConsumption"]
    
    # Test February 15th, 2026
    start_at = "2026-02-15"
    end_at = "2026-02-15"
    
    measure_points = [
        "DailyActiveProduction", "DailyConsumption", 
        "DailyEnergyPurchased", "DailyDischargingEnergy"
    ]
    
    print(f"\nTesting Feb 15th with Granularity 1 and {len(measure_points)} points")
    payload = {
        "deviceSn": target_sn,
        "measurePoints": measure_points,
        "startAt": start_at,
        "endAt": end_at,
        "granularity": 1
    }
    
    resp = requests.post(url, params={"appId": service.app_id}, json=payload, headers=headers)
    data = resp.json()
    
    if data.get('code') in [0, "0", "1000000"]:
        list_data = data.get('dataList', [])
        print(f"SUCCESS: Found {len(list_data)} points.")
        if list_data:
            # Show keys found in first point
            keys = [i['key'] for i in list_data[0]['itemList']]
            print(f"  Keys found: {keys}")
    else:
        code = data.get('code')
        msg = data.get('msg', '').encode('ascii', 'ignore').decode('ascii')
        print(f"FAILED: {code} - {msg}")

if __name__ == "__main__":
    test_granularity()
