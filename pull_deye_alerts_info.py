import os
import django
import logging
import json
import requests
from datetime import datetime, timedelta

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

# Configure logging to show only important info to console
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

from vegrid_app.services.deye_service import DeyeService
from vegrid_app.deye_api import DeyeAPI

def pull_alerts_info():
    """Script to pull and display detailed alert data from Deye Cloud"""
    print("="*60)
    print(" DEYE CLOUD ALERT DATA INVESTIGATION ")
    print("="*60)
    
    service = DeyeService()
    api = DeyeAPI()
    
    try:
        token = service.get_token()
        print(f"Successfully authenticated. Token: {token[:15]}...")
        
        # 1. Get Device/Station List
        print("\n[1] Fetching Device/Station List...")
        stations_resp = service.get_station_list_with_device()
        
        stations_to_check = []
        devices_to_check = []
        
        if stations_resp.get('code') in [0, "0", "1000000"]:
            station_list = stations_resp.get('stationList', stations_resp.get('data', {}).get('list', []))
            print(f"Found {len(station_list)} stations.")
            
            for station in station_list:
                s_id = station.get('id')
                s_name = station.get('name')
                print(f" - Station: {s_name} (ID: {s_id})")
                if s_id:
                    stations_to_check.append((s_id, s_name))
                
                for device in station.get('deviceListItems', []):
                    sn = device.get('deviceSn')
                    print(f"   - Device SN: {sn} (Status: {'Online' if device.get('connectStatus') == 1 else 'Offline'})")
                    if sn:
                        devices_to_check.append(sn)
        else:
            print(f"Error fetching station list: {stations_resp}")
            return

        # 2. Check Station Alerts (Raw)
        print("\n[2] Checking Station Alerts (Raw API Response)...")
        for s_id, s_name in stations_to_check:
            print(f"\n--- Station: {s_name} (ID: {s_id}) ---")
            resp = api.get_station_alarms(token, s_id)
            print(json.dumps(resp, indent=2))
            
            # Check for alternate/old endpoint if 404
            if resp.get('status') == 404 or resp.get('code') == "2101019":
                print(f"Retrying with legacy endpoint for station {s_id}...")
                old_url = f"{api.base_url}/v1.0/station/alarm"
                try:
                    legacy_resp = requests.post(
                        old_url, 
                        params={"appId": api.app_id}, 
                        json={"id": s_id}, 
                        headers=api._get_headers(token)
                    ).json()
                    print("Legacy Response:")
                    print(json.dumps(legacy_resp, indent=2))
                except Exception as e:
                    print(f"Legacy endpoint failed: {e}")

        # 3. Check Device Alerts (Raw)
        print("\n[3] Checking Device Alerts (Raw API Response)...")
        for sn in devices_to_check:
            print(f"\n--- Device SN: {sn} ---")
            resp = api.get_device_alarms(token, sn)
            print(json.dumps(resp, indent=2))
            
            # Check for alternate/old endpoint if 404
            if resp.get('status') == 404 or resp.get('code') == "2101019":
                print(f"Retrying with legacy endpoint for device {sn}...")
                old_url = f"{api.base_url}/v1.0/device/alarm"
                try:
                    legacy_resp = requests.post(
                        old_url, 
                        params={"appId": api.app_id}, 
                        json={"deviceSn": sn}, 
                        headers=api._get_headers(token)
                    ).json()
                    print("Legacy Response:")
                    print(json.dumps(legacy_resp, indent=2))
                except Exception as e:
                    print(f"Legacy endpoint failed: {e}")

        # 4. Summary of Processed Alerts
        print("\n" + "="*60)
        print(" PROCESSED ALERTS SUMMARY ")
        print("="*60)
        processed_alerts = service.get_alerts(save_to_db=False)
        if processed_alerts:
            for alert in processed_alerts:
                print(f"[{alert['date']}] {alert['severity']} - {alert['alert_type']} at {alert['site']}")
                print(f"    Source: {alert['source']} | Status: {alert['status']}")
                print(f"    Message: {alert['message']}")
                print("-" * 30)
        else:
            print("No active alerts found after processing.")

    except Exception as e:
        print(f"\nCRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    pull_alerts_info()
