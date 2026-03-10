import os
import django
import json
from dotenv import load_dotenv

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
load_dotenv(override=True)
django.setup()

from vegrid_app.services.deye_service import DeyeService
from vegrid_app.deye_api import DeyeAPI

def pull_pv_data():
    service = DeyeService()
    api = DeyeAPI()
    
    print(f"Authenticating for {service.username}...")
    token = service.get_token()
    
    if not token:
        print("Failed to obtain token")
        return

    print("Token obtained successfully.")

    # Get station list with device details
    print("Fetching station list with device details...")
    stations_resp = service.get_station_list_with_device()
    
    if stations_resp.get('code') not in [0, "0", "1000000"]:
        print(f"Failed to get station list: {stations_resp.get('msg')}")
        return

    station_list = stations_resp.get('stationList', stations_resp.get('data', {}).get('list', []))
    if not station_list:
        print("No stations found.")
        return

    # Find the non-demo device SN
    device_sn = None
    for station in station_list:
        station_name = station.get('name', '').lower()
        if 'demo' in station_name:
            continue
            
        device_list_items = station.get('deviceListItems', [])
        if device_list_items:
            device_sn = device_list_items[0].get('deviceSn')
            print(f"Using device: {device_sn} from station '{station.get('name')}'")
            break
    
    if not device_sn:
        print("No non-demo devices found. Falling back to the first available device.")
        for station in station_list:
            device_list_items = station.get('deviceListItems', [])
            if device_list_items:
                device_sn = device_list_items[0].get('deviceSn')
                print(f"Using device: {device_sn} from station '{station.get('name')}'")
                break
    
    if not device_sn:
        print("No devices found in any station.")
        return

    # Pull real-time data
    print(f"Pulling real-time data for device: {device_sn}...")
    # Use api.get_device_latest directly or service.get_latest_device_data
    latest_data = api.get_device_latest(token, [device_sn])
    
    if latest_data.get('code') in [0, "0", "1000000"]:
        print("\n--- Real-Time PV Data ---")
        print(json.dumps(latest_data, indent=2))
        
        # Try to extract and display useful metrics
        device_list = latest_data.get('data', []) or latest_data.get('deviceDataList', [])
        if device_list:
            info = device_list[0]
            # Some APIs return key-value pairs in 'dataList'
            if 'dataList' in info:
                print("\nKey Metrics (from dataList):")
                for item in info['dataList']:
                    key = item.get('key')
                    val = item.get('value')
                    unit = item.get('unit', '')
                    if key in ['TotalDCInputPower', 'DailyActiveProduction', 'TotalActiveProduction', 'DCPowerPV1', 'DCPowerPV2']:
                        print(f"- {key}: {val} {unit}")
            else:
                print("\nKey Metrics (from top-level):")
                pv_keys = ['pvPower', 'todayProduction', 'totalProduction', 'pv1Power', 'pv2Power', 'generationPower']
                for key in pv_keys:
                    if key in info:
                        print(f"- {key}: {info[key]}")
    else:
        print(f"Failed to get latest data: {latest_data.get('msg')}")

if __name__ == "__main__":
    pull_pv_data()
