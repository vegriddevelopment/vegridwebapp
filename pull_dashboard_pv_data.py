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

def pull_dashboard_data():
    service = DeyeService()
    api = DeyeAPI()
    
    token = service.get_token()
    if not token:
        logger.error("Failed to obtain token")
        return

    # Five Star Meadows Details
    device_sn = "2510171733"
    station_id = "61776373" 
    
    dashboard_summary = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "station_name": "Five Star Meadows",
        "live_metrics": {},
        "daily_yield": {},
        "station_summary": {}
    }

    # 1. Get Real-Time PV Power (Live Gauge)
    logger.info("Step 1: Fetching Real-Time Device Data...")
    latest_resp = api.get_device_latest(token, [device_sn])
    if latest_resp.get('code') in [0, "0", "1000000"]:
        data_list = latest_resp.get('deviceDataList', [])
        if data_list:
            dev_data = data_list[0]
            # Map the inner dataList to a dict for easier access
            inner_data = {item['key']: item['value'] for item in dev_data.get('dataList', [])}
            
            dashboard_summary["live_metrics"] = {
                "status": "Online" if dev_data.get('deviceState') == 1 else "Offline",
                "pv1Power": float(inner_data.get('DCPowerPV1', 0)),
                "pv2Power": float(inner_data.get('DCPowerPV2', 0)),
                "totalPower": float(inner_data.get('TotalDCInputPower', 0)),
                "loadPower": float(inner_data.get('TotalConsumptionPower', 0)),
                "gridPower": float(inner_data.get('TotalGridPower', 0)),
                "soc": float(inner_data.get('SOC', 0))
            }

    # 2. Get Daily/Monthly Yield (History)
    logger.info("Step 2: Fetching Historical Yield (Daily)...")
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    # Using measure points confirmed in previous tests
    pv_points = ["DailyActiveProduction", "TotalActiveProduction"]
    history_resp = api.get_device_history(
        token=token,
        device_sn=device_sn,
        measure_points=pv_points,
        start_date=start_date,
        end_date=end_date,
        granularity=1 # Daily data points
    )
    
    if history_resp.get('code') in [0, "0", "1000000"]:
        data_list = history_resp.get('dataList', [])
        if data_list:
            # Get the very latest point for "Today's Energy"
            latest_entry = sorted(data_list, key=lambda x: int(x['time']))[-1]
            for item in latest_entry.get('itemList', []):
                dashboard_summary["daily_yield"][item['key']] = float(item['value'])

    # 3. Get Station-Level Overview
    logger.info("Step 3: Fetching Station-Level Overview...")
    station_resp = api.get_station_latest(token, station_id)
    if station_resp.get('code') in [0, "0", "1000000"]:
        st_data = station_resp.get('data', {})
        dashboard_summary["station_summary"] = {
            "totalPower": st_data.get('totalPower', 0),
            "generationToday": st_data.get('generationToday', 0),
            "generationTotal": st_data.get('generationTotal', 0)
        }

    # Final Output
    print("\n" + "="*60)
    print(f"DASHBOARD DATA: {dashboard_summary['station_name']}")
    print("="*60)
    print(json.dumps(dashboard_summary, indent=2))
    print("="*60 + "\n")

if __name__ == "__main__":
    pull_dashboard_data()
