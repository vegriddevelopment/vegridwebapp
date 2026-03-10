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

def test_station_history_daily_for_month():
    service = DeyeService()
    station_id = "61776373"
    token = service.get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    url = f"{service.base_url}/v1.0/station/history"
    
    # Requesting daily data for March 2026
    payload = {
        "stationId": station_id,
        "granularity": 1, # Day
        "startAt": "2026-03-01",
        "endAt": "2026-03-31"
    }
    
    print(f"Requesting daily station history for March 2026...")
    resp = requests.post(url, params={"appId": service.app_id}, json=payload, headers=headers)
    data = resp.json()
    
    if data.get('code') in [0, "0", "1000000"]:
        print("SUCCESS:")
        items = data.get('data', {}).get('items', []) or data.get('dataList', [])
        print(f"Total points returned: {len(items)}")
        
        for i in items[:5]: # Show first 5
             print(json.dumps(i, indent=2))
             
        if items:
            last = items[-1]
            print("LAST ITEM:")
            print(json.dumps(last, indent=2))
        
    else:
        print(f"FAILED: {data}")

if __name__ == "__main__":
    test_station_history_daily_for_month()
