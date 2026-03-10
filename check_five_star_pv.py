import os
import django
import logging
from datetime import datetime, timedelta
import json

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.deye_api import DeyeAPI
from vegrid_app.services.deye_service import DeyeService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_five_star_meadows_pv():
    service = DeyeService()
    api = DeyeAPI()
    
    token = service.get_token()
    if not token:
        logger.error("Failed to obtain token")
        return

    # Specific SN for Five Star Meadows as identified in previous check
    device_sn = "2510171733"
    logger.info(f"Targeting Five Star Meadows (Device: {device_sn})")

    # Measure points to test (focused on PV)
    pv_points = [
        "TotalSolarPower", 
        "DCPowerPV1", 
        "DCPowerPV2", 
        "DailyActiveProduction",
        "TotalActiveProduction"
    ]
    
    end_time = datetime.now()
    # Check last 12 hours (daylight period)
    start_time = end_time - timedelta(hours=12)
    
    logger.info(f"Requesting PV history for {device_sn}...")
    
    history = api.get_device_history(
        token=token,
        device_sn=device_sn,
        measure_points=pv_points,
        start_date=start_time.strftime("%Y-%m-%d"),
        end_date=end_time.strftime("%Y-%m-%d"),
        granularity=1
    )
    
    if history.get('code') not in [0, "0", "1000000"]:
        logger.error(f"Failed to get history: {history.get('msg')}")
        return

    data_list = history.get('dataList', [])
    if not data_list:
        logger.warning("No historical data found for the last 12 hours. Checking realtime...")
        realtime = api.get_device_realtime(token, device_sn)
        print(json.dumps(realtime, indent=2))
        return

    # Filter for non-zero data
    latest_points = {}
    for entry in sorted(data_list, key=lambda x: int(x['time'])):
        for item in entry.get('itemList', []):
            latest_points[item['key']] = float(item['value'])

    print("\n" + "="*45)
    print(f"PV INFO: FIVE STAR MEADOWS ({device_sn})")
    print("-" * 45)
    for key, val in latest_points.items():
        unit = "W" if "Power" in key else "kWh"
        print(f"{key:<25}: {val:>10.2f} {unit}")
    print("="*45 + "\n")

if __name__ == "__main__":
    check_five_star_meadows_pv()
