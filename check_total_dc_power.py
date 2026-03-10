import json
import requests
from datetime import datetime, timedelta
import logging
import time
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Configuration
    BASE_URL = "https://eu1-developer.deyecloud.com"
    APP_ID = "639853817928690176"
    USERNAME = "paul@vegridenergy.com"
    PASSWORD = "Vegrid@2023"
    
    # Hash password (SHA256)
    PASSWORD_HASH = hashlib.sha256(PASSWORD.encode('utf-8')).hexdigest().upper()
    
    # Step 1: Login and get token
    logger.info("Authenticating with Deye API...")
    login_url = f"{BASE_URL}/v1.0/account/token"
    login_params = {"appId": APP_ID}
    login_payload = {
        "appSecret": "66d249a1192a9f0e703ef49e3a41a9ee",
        "password": PASSWORD_HASH,
        "email": USERNAME
    }
    
    login_response = requests.post(
        login_url,
        params=login_params,
        json=login_payload,
        timeout=10
    )
    
    if login_response.status_code != 200:
        logger.error(f"Login failed. Status code: {login_response.status_code}")
        logger.error(login_response.text)
        return
    
    login_data = login_response.json()
    logger.info(f"Login response: {json.dumps(login_data, indent=2)}")
    
    # Check if login was successful
    if login_data.get('code') not in [0, "0", "1000000"] or not login_data.get('success'):
        logger.error("Login failed: " + login_data.get('msg', 'Unknown error'))
        return
    
    token = login_data.get('data', {}).get('token')
    if not token:
        logger.error("No token found in login response")
        return
    
    logger.info(f"Token: {token}")
    logger.info("Deye authentication successful")
    
    # Step 2: Get station list
    logger.info("Getting station list with device details from https://eu1-developer.deyecloud.com/v1.0/station/listWithDevice")
    station_url = f"{BASE_URL}/v1.0/station/listWithDevice"
    station_params = {"appId": APP_ID}
    station_headers = {"Authorization": f"Bearer {token}"}
    
    station_response = requests.get(
        station_url,
        params=station_params,
        headers=station_headers,
        timeout=10
    )
    
    if station_response.status_code != 200:
        logger.error(f"Failed to get station list: {station_response.status_code}")
        logger.error(station_response.text)
        return
    
    station_data = station_response.json()
    logger.info(f"Station list with device response: {json.dumps(station_data, indent=2)}")
    
    if station_data.get('code') not in [0, "0", "1000000"]:
        logger.error(f"Failed to get station list: {station_data.get('msg', 'Unknown error')}")
        return
    
    # Find device SN for "VOLEMI Hybrid Solar System"
    target_station_name = "VOLEMI Hybrid Solar System"
    target_device_sn = None
    
    for station in station_data.get('stationList', []):
        if station.get('name') == target_station_name:
            logger.info(f"Found target station: {station.get('name')}")
            if station.get('deviceTotal') > 0:
                for device in station.get('deviceListItems', []):
                    logger.info(f"Device SN: {device.get('deviceSn')}")
                    target_device_sn = device.get('deviceSn')
            break
    
    if not target_device_sn:
        logger.error("Device not found")
        return
    
    # Step 3: Check TotalDCInputPower from device history
    logger.info("Checking TotalDCInputPower from device history...")
    history_url = f"{BASE_URL}/v1.0/device/history"
    history_params = {"appId": APP_ID}
    history_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=10)
    
    history_payload = {
        "deviceSn": target_device_sn,
        "measurePoints": ["TotalDCInputPower"],
        "startAt": start_time.strftime("%Y-%m-%d"),
        "endAt": end_time.strftime("%Y-%m-%d"),
        "granularity": 1
    }
    
    history_response = requests.post(
        history_url,
        params=history_params,
        json=history_payload,
        headers=history_headers,
        timeout=20
    )
    
    if history_response.status_code == 200:
        history_result = history_response.json()
        logger.info(f"History response: {json.dumps(history_result, indent=2)}")
        
        if history_result.get('code') in [0, "0", "1000000"]:
            data_list = history_result.get('dataList', [])
            if data_list:
                # Get latest data point
                latest_data = sorted(data_list, key=lambda x: int(x['time']))[-1]
                item_list = latest_data.get('itemList', [])
                for item in item_list:
                    if item.get('key') == 'TotalDCInputPower':
                        total_dc_power = float(item.get('value')) / 1000  # Convert to kW
                        logger.info(f"Latest TotalDCInputPower: {total_dc_power:.2f} kW")

if __name__ == "__main__":
    main()