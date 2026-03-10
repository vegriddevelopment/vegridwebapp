
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

def check_station_list_with_weather():
    service = DeyeService()
    try:
        token = service.get_token()
        url = f"{service.base_url}/v1.0/station/list"
        params = {
            "appId": service.app_id,
            "page": 1,
            "size": 20,
            "includeWeather": "true",
            "includeDevice": "true"
        }
        payload = {"page": 1, "size": 20}
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        response = requests.post(url, params=params, json=payload, headers=headers)
        result = response.json()
        logger.info(f"Station List with Weather Response: {json.dumps(result, indent=2)}")
    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == "__main__":
    check_station_list_with_weather()
