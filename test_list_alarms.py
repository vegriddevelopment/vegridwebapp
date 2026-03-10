import os
import django
import requests
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.services.deye_service import DeyeService

service = DeyeService()
token = service.get_token()
base_url = service.base_url
app_id = service.app_id

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

url = f"{base_url}/v1.0/station/listWithDevice"
payload = {"page": 1, "size": 20, "deviceType": "INVERTER"}
params = {"appId": app_id}

print(f"\n--- Testing {url} ---")
response = requests.post(url, params=params, json=payload, headers=headers)
print(f"Status: {response.status_code}")
data = response.json()
for station in data.get('stationList', []):
    print(f"\nStation: {station.get('name')} (ID: {station.get('id')})")
    for device in station.get('deviceListItems', []):
        print(f"  Device: {device.get('deviceSn')}")
        # Check for alarm fields
        for key in device.keys():
            if 'alarm' in key.lower() or 'status' in key.lower() or 'connect' in key.lower():
                print(f"    {key}: {device[key]}")
