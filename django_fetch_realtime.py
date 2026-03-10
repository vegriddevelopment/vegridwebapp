import os
import django
import requests
import json

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from django.conf import settings

def deep_investigate_pv():
    baseurl = "https://eu1-developer.deyecloud.com/v1.0"
    app_id = settings.DEYE_APP_ID
    app_secret = settings.DEYE_APP_SECRET
    username = settings.DEYE_USERNAME
    password = settings.DEYE_PASSWORD
    device_sn = "2510171733" 

    print(f"Authenticating for {username}...")
    
    import hashlib
    password_hash = hashlib.sha256(password.encode()).hexdigest().lower()
    
    auth_url = f"{baseurl}/account/token"
    auth_payload = {
        "appSecret": app_secret,
        "password": password_hash,
        "email": username
    }
    
    try:
        auth_resp = requests.post(auth_url, params={"appId": app_id}, json=auth_payload)
        auth_result = auth_resp.json()
        token = auth_result.get('accessToken') or auth_result.get('data', {}).get('accessToken')
        
        if not token:
            print(f"Auth Failed: {auth_result}")
            return

        headers = {"Authorization": f"bearer {token}", "Content-Type": "application/json"}
        
        # 1. Get ALL Latest Data points
        latest_url = f"{baseurl}/device/latest"
        latest_resp = requests.post(latest_url, headers=headers, json={"deviceList": [device_sn]})
        latest_data = latest_resp.json()
        
        print(f"\n--- FULL DATA INVESTIGATION FOR {device_sn} ---")
        device_data_list = latest_data.get('deviceDataList', [])
        if device_data_list:
            points = device_data_list[0].get('dataList', [])
            
            # Group keys for better visibility
            pv_keys = []
            other_power_keys = []
            all_keys = []

            for p in points:
                key = p.get('key')
                val = p.get('value')
                unit = p.get('unit', '')
                all_keys.append(f"{key}: {val} {unit}")
                
                if 'PV' in key or 'DC' in key:
                    pv_keys.append(f"  {key}: {val} {unit}")
                elif 'Power' in key:
                    other_power_keys.append(f"  {key}: {val} {unit}")

            print("\n[PV / DC Related Keys]")
            for k in sorted(pv_keys):
                print(k)

            print("\n[Other Power Related Keys]")
            for k in sorted(other_power_keys):
                print(k)

            # 2. Check for other devices in the same station
            print("\n--- Checking for other devices in the station ---")
            station_url = f"{baseurl}/station/listWithDevice"
            station_resp = requests.post(station_url, params={"appId": app_id}, headers=headers, json={"page": 1, "size": 10})
            station_data = station_resp.json()
            
            for station in station_data.get('stationList', []):
                # We know your station name from previous runs
                if "Five Star" in station.get('name'):
                    print(f"Station: {station.get('name')} (ID: {station.get('id')})")
                    for dev in station.get('deviceListItems', []):
                        sn = dev.get('deviceSn')
                        dtype = dev.get('deviceType')
                        if sn != device_sn:
                            print(f"  Found other device: {sn} ({dtype})")
                            # Pull data for this other device too
                            dev_latest = requests.post(latest_url, headers=headers, json={"deviceList": [sn]})
                            d_points = dev_latest.json().get('deviceDataList', [{}])[0].get('dataList', [])
                            for dp in d_points:
                                if 'Power' in dp.get('key') or 'PV' in dp.get('key'):
                                    print(f"    {dp.get('key')}: {dp.get('value')} {dp.get('unit')}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    deep_investigate_pv()
