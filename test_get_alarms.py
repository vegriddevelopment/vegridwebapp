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

# Device SN from previous tests
device_sn = "2510171733" # VOLEMI

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

url = f"{base_url}/v1.0/device/alarm"
payload = {"deviceSn": device_sn, "page": 1, "size": 20}
params = {"appId": app_id}

print(f"\n--- Testing {url} for device {device_sn} ---")
response = requests.post(url, params=params, json=payload, headers=headers)
print(f"Status: {response.status_code}")
try:
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
except:
    print(f"Response (text): {response.text}")
