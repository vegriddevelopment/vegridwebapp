import os
import django
import logging
import json

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.deye_api import DeyeAPI
from vegrid_app.services.deye_service import DeyeService

def check_measure_points():
    service = DeyeService()
    api = DeyeAPI()
    
    token = service.get_token()
    if not token:
        print("Failed to obtain token")
        return

    device_sn = "2510171733"
    
    print(f"Checking measure points for device {device_sn}...")
    resp = api.get_device_measure_points(token, device_sn)
    print(json.dumps(resp, indent=2))
    
    print("\nChecking latest data for device...")
    latest_resp = api.get_device_latest(token, [device_sn])
    print(json.dumps(latest_resp, indent=2))

if __name__ == "__main__":
    check_measure_points()
