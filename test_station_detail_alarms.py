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
url = f"{base_url}/v1.0/station/detail"
params = {"appId": app_id, "id": station_id}

print(f"\n--- Testing {url} ---")
response = requests.get(url, params=params, headers=headers)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
