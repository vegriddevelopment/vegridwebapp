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

def check_pv_data():
    service = DeyeService()
    api = DeyeAPI()
    
    token = service.get_token()
    
    if not token:
        logger.error("Failed to obtain token")
        return

    # Get a real device SN
    stations_resp = service.get_station_list_with_device()
    device_sn = None
    if stations_resp.get('code') in [0, "0", "1000000"]:
        station_list = stations_resp.get('stationList', stations_resp.get('data', {}).get('list', []))
        for station in station_list:
            if station.get('deviceListItems'):
                device_sn = station.get('deviceListItems')[0].get('deviceSn')
                break
    
    if not device_sn:
        logger.error("No device found")
        return

    # Step 1: Check Latest endpoint
    logger.info("\n--- Checking Device Latest Endpoint ---")
    latest_resp = api.get_device_latest(token, [device_sn])
    if latest_resp.get('code') in [0, "0", "1000000"]:
        data = latest_resp.get('data', [])
        if data:
            device_data = data[0]
            logger.info("Latest Data Keys Found:")
            interesting_keys = ['pvPower', 'productionPower', 'generationPower', 'todayProduction', 'totalProduction', 'pv1Power', 'pv2Power']
            for key in interesting_keys:
                if key in device_data:
                    logger.info(f"✅ {key}: {device_data[key]}")
                else:
                    # Check for case-insensitive match
                    found = False
                    for actual_key in device_data.keys():
                        if actual_key.lower() == key.lower():
                            logger.info(f"✅ {actual_key} (matches {key}): {device_data[actual_key]}")
                            found = True
                    if not found:
                        logger.info(f"❌ {key}: Not found")
        else:
            logger.warning("No data returned from latest endpoint")
    else:
        logger.error(f"Latest endpoint error: {latest_resp.get('msg')}")

    # Step 2: Check History endpoint (from before)
    logger.info("\n--- Checking Device History (Measure Points) ---")
    pv_points = ["TotalSolarPower", "DCPowerPV1", "DCPowerPV2", "DCPowerPV3", "DCPowerPV4"]
    
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24) # Check last 24 hours to ensure we hit daylight
    
    logger.info(f"Requesting history for points: {pv_points}")
    
    # Use api instance directly to call get_device_history
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
        logger.warning("No historical data found for the last 24 hours.")
        # Try realtime as fallback
        realtime = api.get_device_realtime(token, device_sn)
        logger.info(f"Realtime data: {json.dumps(realtime, indent=2)}")
        return

    # Analyze which points have non-zero/valid data
    results = {point: {"count": 0, "max_val": 0, "has_data": False} for point in pv_points}
    
    for entry in data_list:
        for item in entry.get('itemList', []):
            key = item.get('key')
            val = float(item.get('value', 0))
            if key in results:
                results[key]["count"] += 1
                if val > results[key]["max_val"]:
                    results[key]["max_val"] = val
                if val > 0:
                    results[key]["has_data"] = True

    logger.info("\nPV Data Check Results:")
    found_any = False
    for point, res in results.items():
        status = "✅ DATA FOUND" if res["has_data"] else "❌ NO DATA (or zero)"
        logger.info(f"- {point}: {status} (Max value: {res['max_val']}, Data points: {res['count']})")
        if res["has_data"]:
            found_any = True
            
    if found_any:
        # Suggest the best point
        best_point = max(results, key=lambda k: results[k]["max_val"])
        logger.info(f"\nRecommended measurement for PV: {best_point}")
    else:
        logger.warning("\nNo PV data found in history. It might be night time or the device is offline.")

if __name__ == "__main__":
    check_pv_data()
