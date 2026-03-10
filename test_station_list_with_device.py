import os
import django
import json
from django.core.cache import cache

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.services.deye_service import DeyeService

# Clear cache to get fresh token
cache.delete('deye_access_token')
cache.delete('deye_token_expiry')

service = DeyeService()
service._token = None

print("=== Testing get_station_list_with_device ===")
station_list = service.get_station_list_with_device()
print(json.dumps(station_list, indent=2))

print("\n=== Checking devices in station list ===")
if station_list.get('code') in [0, "0", "1000000"]:
    for station in station_list.get('stationList', []):
        print(f"\nStation: {station.get('name')}")
        for device in station.get('deviceListItems', []):
            print(f"  Device SN: {device.get('deviceSn')}")
            print(f"  Device Type: {device.get('deviceType')}")
            print(f"  Device Name: {device.get('deviceName')}")
