import os
import django
from dotenv import load_dotenv

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
load_dotenv(override=True)
django.setup()

from vegrid_app.services.deye_service import DeyeService

def list_all_stations():
    service = DeyeService()
    resp = service.get_station_list_with_device()
    
    # Check both potential list locations in response
    station_list = resp.get('stationList', resp.get('data', {}).get('list', []))
    
    print(f"\nTotal Stations Found: {len(station_list)}")
    for i, s in enumerate(station_list, 1):
        print(f"{i}. Name: {s.get('name')}")
        print(f"   ID: {s.get('id')}")
        devices = s.get('deviceListItems', [])
        print(f"   Devices: {len(devices)}")
        for d in devices:
            print(f"     - SN: {d.get('deviceSn')} (Type: {d.get('deviceType')})")

if __name__ == "__main__":
    list_all_stations()
