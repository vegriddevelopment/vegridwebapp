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

from django.conf import settings
from vegrid_app.services.deye_service import DeyeService

def test_raw_endpoints():
    service = DeyeService()
    token = service.get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # We will try both settings.DEYE_API_BASE_URL and the one from service just in case
    # Actually service uses settings.DEYE_API_BASE_URL which is https://api.deyecloud.com
    # But get_token logs showed https://eu1-developer.deyecloud.com
    base_urls = ["https://eu1-developer.deyecloud.com", "https://api.deyecloud.com"]
    
    station_id = 61776373 # Five Star Meadows
    
    for base in base_urls:
        url = f"{base}/v1.0/station/latest"
        logger.info(f"Testing: {url}")
        
        # Try POST with stationId as string
        try:
            payload = {"stationId": str(station_id)}
            resp_post = requests.post(url, params={"appId": service.app_id}, json=payload, headers=headers)
            logger.info(f"  POST station/latest Status: {resp_post.status_code}")
            data = resp_post.json()
            logger.info(f"  POST station/latest Response: {data}")
        except Exception as e:
            logger.error(f"  Error: {str(e)}")
            
        url_list = f"{base}/v1.0/station/list"
        logger.info(f"Testing: {url_list} with includeWeather")
        try:
            params = {"appId": service.app_id, "includeWeather": "true"}
            payload = {"page": 1, "size": 10}
            resp = requests.post(url_list, params=params, json=payload, headers=headers)
            logger.info(f"  POST station/list Status: {resp.status_code}")
            data = resp.json()
            if data.get('code') in [0, "0", "1000000"]:
                stations = data.get('stationList', [])
                for s in stations:
                    if s.get('id') == station_id:
                        logger.info(f"  Station {station_id} in list keys: {list(s.keys())}")
        except Exception as e:
            logger.error(f"  Error: {str(e)}")



if __name__ == "__main__":
    test_raw_endpoints()
