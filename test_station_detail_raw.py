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

def test_station_detail_raw():
    service = DeyeService()
    try:
        token = service.get_token()
        station_ids = [61188657, 61776373]
        
        for station_id in station_ids:
            logger.info(f"\n=== Testing station detail for station {station_id} ===")
            
            # Try station detail endpoint
            url = f"{service.base_url}/v1.0/station/detail"
            params = {
                "appId": service.app_id,
                "id": station_id
            }
            payload = {"id": station_id}
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, params=params, json=payload, headers=headers)
            result = response.json()
            
            logger.info(f"Station Detail Response: {json.dumps(result, indent=2)}")
            
            # Check if there's weather data in the response
            data = result.get('data', {})
            logger.info(f"Data keys: {list(data.keys())}")
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == "__main__":
    test_station_detail_raw()
