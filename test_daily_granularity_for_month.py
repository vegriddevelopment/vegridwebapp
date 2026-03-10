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

def test_daily_granularity_for_month():
    service = DeyeService()
    device_sn = "2510171733"
    token = service.get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    url = f"{service.base_url}/v1.0/device/history"
    
    # Requesting daily data for March 2026
    payload = {
        "deviceSn": device_sn,
        "granularity": 1, # Day
        "startAt": "2026-03-01",
        "endAt": "2026-03-31",
        "measurePoints": ["DailyActiveProduction", "DailyConsumption", "DailyChargingEnergy", "DailyDischargingEnergy", "DailyEnergyPurchased"]
    }
    
    print(f"Requesting daily device history for March 2026...")
    resp = requests.post(url, params={"appId": service.app_id}, json=payload, headers=headers)
    data = resp.json()
    
    if data.get('code') in [0, "0", "1000000"]:
        print("SUCCESS:")
        items = data.get('dataList', [])
        print(f"Total points returned: {len(items)}")
        
        daily_sums = {
            "generation": 0,
            "consumption": 0,
            "discharge": 0,
            "grid": 0
        }
        
        # We need to pick the last entry of each day to get daily totals
        daily_items = {}
        for point in items:
            ts = int(point.get('time', 0))
            if ts == 0: continue
            dt = datetime.fromtimestamp(ts)
            day_key = dt.strftime("%Y-%m-%d")
            
            if day_key not in daily_items or ts > daily_items[day_key]['time']:
                daily_items[day_key] = point
                daily_items[day_key]['time'] = ts

        print(f"Unique days found: {len(daily_items)}")
        
        for day, point in sorted(daily_items.items()):
            day_gen = 0
            day_cons = 0
            day_dis = 0
            day_grid = 0
            for item in point.get('itemList', []):
                val = float(item.get('value', 0))
                if item['key'] == 'DailyActiveProduction': day_gen = val
                elif item['key'] == 'DailyConsumption': day_cons = val
                elif item['key'] == 'DailyDischargingEnergy': day_dis = val
                elif item['key'] == 'DailyEnergyPurchased': day_grid = val
            
            print(f"{day}: Gen={day_gen}, Cons={day_cons}, Dis={day_dis}, Grid={day_grid}")
            daily_sums["generation"] += day_gen
            daily_sums["consumption"] += day_cons
            daily_sums["discharge"] += day_dis
            daily_sums["grid"] += day_grid
            
        print("\nTOTAL SUMS (Daily Aggregation):")
        print(json.dumps(daily_sums, indent=2))
        
    else:
        print(f"FAILED: {data}")

if __name__ == "__main__":
    test_daily_granularity_for_month()
