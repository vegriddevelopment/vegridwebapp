import os
import django
import json
from dotenv import load_dotenv

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
load_dotenv(override=True)
django.setup()

from vegrid_app.services.deye_service import DeyeService
from django.core.cache import cache

def list_devices():
    # Force clear cache to get a fresh token
    cache.delete('deye_access_token')
    cache.delete('deye_token_expiry')
    
    service = DeyeService()
    service._token = None # Clear instance cache too
    print(f"Fetching devices for account: {service.username}")
    
    try:
        # Check authentication first
        token = service.get_token()
        print(f"Token obtained: {token[:10]}...")
        
        # Get account info
        acc_info = service.get_account_info()
        print(f"Account Info: {json.dumps(acc_info, indent=2)}")
        
        # Get station list
        station_list_resp = service.get_station_list()
        print(f"Station List Response: {json.dumps(station_list_resp, indent=2)}")
        
        if station_list_resp.get('code') in [0, "0", "1000000"]:
            stations = station_list_resp.get('stationList', [])
            print(f"\nFound {len(stations)} stations. Fetching devices for each...")
            for station in stations:
                s_id = station.get('id')
                s_name = station.get('name')
                print(f"\nStation: {s_name} (ID: {s_id})")
                
                # Get station detail
                detail = service.get_station_detail_by_id(s_id)
                print(f"  Station Detail: {json.dumps(detail, indent=2)}")
                
                dev_resp = service.get_station_devices(s_id)
                print(f"  Devices Response: {json.dumps(dev_resp, indent=2)}")
                
                if dev_resp.get('code') in [0, "0", "1000000"]:
                    dev_list = dev_resp.get('deviceList', [])
                    for d in dev_list:
                        print(f"  - Device Name: {d.get('name')}")
                        print(f"    SN: {d.get('deviceSn')}")
                        print(f"    Type: {d.get('deviceType')}")
        else:
            print(f"Error fetching devices: {result.get('msg')}")
            
    except Exception as e:
        print(f"Service Error: {str(e)}")

if __name__ == "__main__":
    list_devices()
