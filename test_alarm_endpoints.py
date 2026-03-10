import os
import django
import json
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.services.deye_service import DeyeService
from vegrid_app.deye_api import DeyeAPI
from django.core.cache import cache

# Clear cache to get fresh token
cache.delete('deye_access_token')
cache.delete('deye_token_expiry')

device_sn = "2510171733"
station_id = "61776373"

print(f"=== Testing alarm endpoints for device: {device_sn} (station: {station_id}) ===")

try:
    service = DeyeService()
    service._token = None
    api = DeyeAPI()
    token = service.get_token()
    
    print("\n--- 1. Testing device alarm endpoint ---")
    resp = api.get_device_alarms(token, device_sn)
    print(f"Response status: {resp.get('status')}")
    print(f"Response code: {resp.get('code')}")
    print(f"Response: {json.dumps(resp, indent=2)}")
    
    print("\n--- 2. Testing station alarm endpoint ---")
    resp = api.get_station_alarms(token, station_id)
    print(f"Response status: {resp.get('status')}")
    print(f"Response code: {resp.get('code')}")
    print(f"Response: {json.dumps(resp, indent=2)}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    print(traceback.format_exc())
