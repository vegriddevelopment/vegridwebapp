
import os
import django
import logging
import json
import requests

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from vegrid_app.services.deye_service import DeyeService

def check_station_detail_post():
    service = DeyeService()
    try:
        token = service.get_token()
        stations_resp = service.get_station_list()
        if stations_resp.get('code') in [0, "0", "1000000"]:
            station_list = stations_resp.get('stationList', [])
            if station_list:
                station_id = station_list[0].get('id')
                logger.info(f"Checking detail for station {station_id} using POST")
                
                url = f"{service.base_url}/v1.0/station/detail"
                params = {"appId": service.app_id}
                payload = {"id": station_id}
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
                response = requests.post(url, params=params, json=payload, headers=headers)
                result = response.json()
                logger.info(f"Station Detail (POST) Response: {json.dumps(result, indent=2)}")
            else:
                logger.error("No stations found")
        else:
            logger.error(f"Failed to get station list: {stations_resp}")
    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == "__main__":
    check_station_detail_post()
