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

station_id = "61776373"

print(f"=== Testing station detail for: {station_id} ===")

try:
    service = DeyeService()
    service._token = None
    
    resp = service.get_station_detail(station_id)
    print(json.dumps(resp, indent=2))
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    print(traceback.format_exc())
