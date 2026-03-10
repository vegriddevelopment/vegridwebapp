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

station_id = 61776373
urls = [
    f"{base_url}/v1.0/station/alarm",
    f"{base_url}/v1.0/station/alarm/list",
    f"{base_url}/v1.0/device/alarm/list",
    f"{base_url}/v1.0/alarm/list",
    f"{base_url}/v1.0/station/alarmList"
]

for url in urls:
    print(f"\n--- Testing {url} ---")
    payload = {"stationId": station_id, "page": 1, "size": 20}
    params = {"appId": app_id}
    
    try:
        response = requests.post(url, params=params, json=payload, headers=headers, timeout=5)
        print(f"POST ({response.status_code}): {response.text}")
        
        # Also try GET
        response_get = requests.get(url, params={"appId": app_id, "stationId": station_id}, headers=headers, timeout=5)
        print(f"GET ({response_get.status_code}): {response_get.text}")
    except Exception as e:
        print(f"Error: {e}")
