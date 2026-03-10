import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.services.deye_service import DeyeService
from django.core.cache import cache

# Clear cache to get fresh token
cache.delete('deye_access_token')
cache.delete('deye_token_expiry')

service = DeyeService()
service._token = None

device_sn = "2510171733"
print(f"=== Testing get_alerts for device: {device_sn} ===")

try:
    alerts = service.get_alerts(device_sn=device_sn, save_to_db=False)
    print(f"Successfully retrieved {len(alerts)} alerts")
    print(json.dumps(alerts, indent=2))
except Exception as e:
    print(f"Error: {e}")
    import traceback
    print(traceback.format_exc())
