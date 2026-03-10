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

def check_station_detail_weather():
    service = DeyeService()
    try:
        # We know station IDs from previous run: 61188657, 61776373
        station_ids = [61188657, 61776373]
        
        for s_id in station_ids:
            logger.info(f"Checking latest for station {s_id}...")
            result = service.get_station_latest(s_id)
            
            if result.get('code') in [0, "0", "1000000"]:
                data = result.get('data', {})
                logger.info(f"Station {s_id} Latest Data Keys: {list(data.keys())}")
                # Check for weather related fields in station/latest
                weather_fields = ['tmp', 'weatherName', 'weatherIcon', 'weather', 'temp', 'temperature']
                for f in weather_fields:
                    if f in data:
                        logger.info(f"  Found {f}: {data.get(f)}")
            else:
                logger.error(f"Failed to get latest for {s_id}: {result}")


                
    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == "__main__":
    check_station_detail_weather()
