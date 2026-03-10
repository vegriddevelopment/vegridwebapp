import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.services.deye_service import DeyeService
from vegrid_app.deye_api import DeyeAPI
from django.core.cache import cache

# Clear cache to get fresh token
cache.delete('deye_access_token')
cache.delete('deye_token_expiry')

device_sn = "2510171733"

print(f"=== Testing device real-time data for: {device_sn} ===")

try:
    service = DeyeService()
    service._token = None
    api = DeyeAPI()
    token = service.get_token()
    
    resp = api.get_device_realtime(token, device_sn)
    print(json.dumps(resp, indent=2))
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    print(traceback.format_exc())
