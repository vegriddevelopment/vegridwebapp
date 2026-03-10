import os
import sys
import django
import json
import requests

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.services.deye_service import DeyeService

def check_measure_points():
    service = DeyeService()
    target_sn = "2510171733"
    token = service.get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    url = f"{service.base_url}/v1.0/device/measurePoints"
    payload = {"deviceSn": target_sn}
    
    print(f"Checking measure points for {target_sn}...")
    resp = requests.post(url, params={"appId": service.app_id}, json=payload, headers=headers)
    data = resp.json()
    
    if data.get('code') in [0, "0", "1000000"]:
        points = data.get('data', [])
        print(f"Found {len(points)} measure points.")
        # Filter for energy-related points
        energy_points = [p for p in points if any(word in p.get('name', '').lower() or word in p.get('key', '').lower() for word in ['energy', 'production', 'consumption', 'daily', 'generation'])]
        for p in sorted(energy_points, key=lambda x: x.get('key', '')):
            print(f"Key: {p.get('key'):<25} | Name: {p.get('name')}")
    else:
        print(f"FAILED: {data}")

if __name__ == "__main__":
    check_measure_points()
