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

def check_month_data():
    service = DeyeService()
    print("--- Deye Month Data Availability Check ---")
    
    try:
        # 1. Get Station List
        print("Step 1: Fetching Station List...")
        stations_resp = service.get_station_list_with_device()
        stations = stations_resp.get('stationList', stations_resp.get('data', {}).get('list', []))
        
        if not stations:
            print("FAILED: No stations found.")
            return
            
        station = stations[0]
        station_id = station.get('id')
        station_name = station.get('name')
        device_sns = [d.get('deviceSn') for d in station.get('deviceListItems', [])]
        
        print(f"Testing Station: {station_name} (ID: {station_id})")
        print(f"Associated Devices: {device_sns}")

        # 2. Test Method A: Native Station Month API
        month = datetime.now().strftime("%Y-%m")
        print(f"\nStep 2: Testing Native Station API (/v1.0/station/energy/month) for {month}...")
        
        token = service.get_token()
        url = f"{service.base_url}/v1.0/station/energy/month"
        payload = {"id": station_id, "month": month}
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        try:
            resp = requests.post(url, params={"appId": service.app_id}, json=payload, headers=headers, timeout=15)
            result = resp.json()
            if result.get('code') in [0, "0", "1000000"]:
                items = result.get('data', {}).get('items', [])
                print(f"SUCCESS: Station API returned {len(items)} days of data.")
                if items:
                    print(f"Fields available in first item: {list(items[0].keys())}")
            else:
                print(f"FAILED: Station API returned code {result.get('code')}: {result.get('msg')}")
        except Exception as e:
            print(f"ERROR: Native API call failed: {str(e)}")

        # 3. Test Method B: Device History Aggregation (The Reliable Way)
        print(f"\nStep 3: Testing Device History Fallback (Aggregation) for {month}...")
        if not device_sns:
            print("SKIP: No devices to query history for.")
        else:
            # We use the service's existing logic
            history_month_resp = service._get_station_energy_from_history(station_id, 'month', month)
            if history_month_resp.get('code') in [0, "0", "1000000"]:
                items = history_month_resp.get('data', {}).get('items', [])
                print(f"SUCCESS: History Fallback returned {len(items)} days of data.")
                
                if items:
                    print("\nLatest Day Data Point Check:")
                    latest = items[-1]
                    print(f"  - Date: {latest.get('time')}")
                    print(f"  - Generation: {latest.get('generation')} kWh")
                    print(f"  - Consumption: {latest.get('consumption')} kWh")
                    print(f"  - Discharge (Storage): {latest.get('storage')} kWh")
                    print(f"  - Grid: {latest.get('grid')} kWh")
                    
                    features = ['generation', 'consumption', 'storage', 'grid']
                    present = [f for f in features if latest.get(f) is not None]
                    print(f"\nSummary: Found {len(present)}/4 features with values.")
                    if len(present) == 4:
                        print("CONCLUSION: ALL 4 features are successfully pullable for Month data.")
                    else:
                        print(f"CONCLUSION: Partial success. Missing: {list(set(features) - set(present))}")
            else:
                print(f"FAILED: History Fallback returned error: {history_month_resp}")

    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_month_data()
