import os
import sys
import django
import json

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.services.deye_service import DeyeService

def test_service_monthly_fallback():
    service = DeyeService()
    station_id = "61776373"
    
    print(f"Testing _get_station_energy_from_history for station {station_id} (Month period)...")
    # Using the current month
    result = service._get_station_energy_from_history(station_id, 'month', '2026-03')
    
    if result.get('code') == 0:
        print("SUCCESS:")
        items = result.get('data', {}).get('items', [])
        print(f"Total days returned: {len(items)}")
        
        sums = {"gen": 0, "cons": 0, "dis": 0, "grid": 0}
        for item in items:
            print(f"  {item['time'][:10]}: Gen={item['generation']}, Cons={item['consumption']}, Dis={item['storage']}, Grid={item['grid']}")
            sums["gen"] += item['generation']
            sums["cons"] += item['consumption']
            sums["dis"] += item['storage']
            sums["grid"] += item['grid']
            
        print("\nTOTAL AGGREGATED SUMS:")
        print(json.dumps(sums, indent=2))
    else:
        print(f"FAILED: {result}")

if __name__ == "__main__":
    test_service_monthly_fallback()
