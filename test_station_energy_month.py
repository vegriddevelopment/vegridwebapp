import os
import sys
import django
import requests
import json

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.services.deye_service import DeyeService

def test_station_energy_month():
    service = DeyeService()
    station_id = "61776373"
    token = service.get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    url = f"{service.base_url}/v1.0/station/energy/month"
    
    payload = {
        "id": station_id,
        "month": "2026-03"
    }
    
    print(f"Requesting station energy month for 61776373...")
    resp = requests.post(url, params={"appId": service.app_id}, json=payload, headers=headers)
    data = resp.json()
    
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    test_station_energy_month()
