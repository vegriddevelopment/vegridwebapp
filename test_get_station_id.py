import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.services.deye_service import DeyeService
from django.core.cache import cache

# Clear cache to get fresh token
cache.delete('deye_access_token')
cache.delete('deye_token_expiry')

device_sn = "2510171733"

print(f"=== Testing get_station_id_by_device_sn for device: {device_sn} ===")

try:
    service = DeyeService()
    service._token = None
    
    station_id = service.get_station_id_by_device_sn(device_sn)
    print(f"Station ID: {station_id}")
    
    device_sns = service._get_device_sns_from_station_id(station_id)
    print(f"Device SNs for station: {device_sns}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    print(traceback.format_exc())
