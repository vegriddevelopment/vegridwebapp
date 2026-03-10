import os
import django
import logging
import json

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.deye_api import DeyeAPI
from vegrid_app.services.deye_service import DeyeService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_raw_latest_pv():
    service = DeyeService()
    api = DeyeAPI()
    
    token = service.get_token()
    if not token:
        logger.error("Failed to obtain token")
        return

    # Five Star Meadows Details
    device_sn = "2510171733"
    
    print(f"\nRequesting RAW data from /v1.0/device/latest for SN: {device_sn}")
    
    # Payload as per your requirement
    latest_resp = api.get_device_latest(token, [device_sn])
    
    print("\n" + "="*60)
    print("RAW API RESPONSE (device/latest)")
    print("="*60)
    print(json.dumps(latest_resp, indent=2))
    print("="*60)

    if latest_resp.get('code') in [0, "0", "1000000"]:
        data_list = latest_resp.get('data', [])
        if data_list:
            dev_data = data_list[0]
            print("\nEXTRACTED PV INFO:")
            print(f"pv1Power  : {dev_data.get('pv1Power', 'NOT FOUND')}")
            print(f"pv2Power  : {dev_data.get('pv2Power', 'NOT FOUND')}")
            print(f"totalPower: {dev_data.get('totalPower', 'NOT FOUND')}")
        else:
            print("\nWARNING: The 'data' array in the response is empty.")
    else:
        print(f"\nERROR: API returned code {latest_resp.get('code')}: {latest_resp.get('msg')}")

if __name__ == "__main__":
    check_raw_latest_pv()
