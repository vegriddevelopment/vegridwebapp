import os
import django
import json
from django.core.cache import cache

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.deye_api import DeyeAPI
from vegrid_app.services.deye_service import DeyeService

# Clear cache to get fresh token
cache.delete('deye_access_token')
cache.delete('deye_token_expiry')

service = DeyeService()
service._token = None
api = DeyeAPI()
token = service.get_token()
print(f"Token: {token[:10]}...")

print("\n=== Testing device list ===")
device_list_resp = api.get_device_list(token)
print(json.dumps(device_list_resp, indent=2))

print("\n=== Testing realtime data for 2510171733 ===")
realtime_resp = api.get_device_realtime(token, "2510171733")
print(json.dumps(realtime_resp, indent=2))

print("\n=== Testing alarm list endpoint directly ===")
alarm_list_resp = api.get_device_alarms(token, "2510171733")
print(json.dumps(alarm_list_resp, indent=2))
