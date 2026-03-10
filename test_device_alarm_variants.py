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

device_sn = "2510171733"
urls = [
    f"{base_url}/v1.0/device/alarms",
    f"{base_url}/v1.0/device/alarm/list",
    f"{base_url}/v1.0/device/alarmList",
    f"{base_url}/v1.0/device/history/alarm",
    f"{base_url}/v1.0/device/event",
]

for url in urls:
    print(f"\n--- Testing {url} ---")
    payload = {"deviceSn": device_sn, "page": 1, "size": 20}
    params = {"appId": app_id}
    
    try:
        response = requests.post(url, params=params, json=payload, headers=headers, timeout=5)
        print(f"POST ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"Error: {e}")
