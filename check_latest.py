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

def check_latest_data():
    service = DeyeService()
    target_sn = "2510171733"
    token = service.get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    url = f"{service.base_url}/v1.0/device/realtime"
    payload = {"deviceSn": target_sn}
    
    print(f"Checking latest data for {target_sn}...")
    resp = requests.post(url, params={"appId": service.app_id}, json=payload, headers=headers)
    data = resp.json()
    
    if data.get('code') in [0, "0", "1000000"]:
        items = data.get('data', [])
        print(f"Found {len(items)} measure points in real-time.")
        for i in items:
            key = i.get('key')
            val = i.get('value')
            name = i.get('name')
            # Look for energy-related keys
            if any(word in key.lower() or word in name.lower() for word in ['daily', 'total', 'energy', 'production', 'consumption', 'generation']):
                print(f"Key: {key:<25} | Name: {name:<25} | Value: {val}")
    else:
        print(f"FAILED: {data}")

if __name__ == "__main__":
    check_latest_data()
