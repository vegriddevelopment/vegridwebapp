import os
import sys
import django
import json
from datetime import datetime

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.services.deye_service import DeyeService

def test_month_data():
    service = DeyeService()
    print("--- Deye Month Data Test ---")
    
    try:
        # 1. Get Station List
        print("Fetching Station List...")
        stations_resp = service.get_station_list_with_device()
        stations = stations_resp.get('stationList', stations_resp.get('data', {}).get('list', []))
        
        if not stations:
            print("No stations found.")
            return
            
        station_id = stations[0].get('id')
        station_name = stations[0].get('name')
        print(f"\nChecking Station: {station_name} (ID: {station_id})")
        
        # 2. Get Month Data
        month = datetime.now().strftime("%Y-%m")
        print(f"Calling get_station_energy_month for {month}...")
        month_resp = service.get_station_energy_month(station_id, month)
        
        if month_resp.get('code') in [0, "0", "1000000"]:
            data = month_resp.get('data', {})
            items = data.get('items', [])
            print(f"SUCCESS: Found {len(items)} days of data.")
            
            if items:
                print("\nSample day data (latest):")
                latest = items[-1]
                print(json.dumps(latest, indent=2))
                
                # Check if all 4 features are present
                features = ['generation', 'consumption', 'storage', 'grid']
                missing = [f for f in features if f not in latest or latest[f] == 0]
                if missing:
                    print(f"\nWARNING: Some features might be missing or 0: {missing}")
                else:
                    print("\nAll 4 features found with values!")
        else:
            print(f"Error fetching month data: {month_resp}")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_month_data()
