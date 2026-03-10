import os
import django
import logging
import json

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from vegrid_app.services.deye_service import DeyeService
from vegrid_app.models import DeyeDevice

def check_site_name_sync():
    """Check if DeyeDevice names match Deye Cloud station names"""
    logger.info("Checking site name synchronization...")
    
    service = DeyeService()
    devices = DeyeDevice.objects.all()
    
    if not devices.exists():
        logger.warning("No Deye devices found in database")
        return
        
    try:
        # Get station list from Deye Cloud
        stations_resp = service.get_station_list()
        if stations_resp.get('code') not in [0, "0", "1000000"]:
            logger.error(f"Failed to get station list from Deye Cloud: {stations_resp.get('msg')}")
            return
            
        station_list = stations_resp.get('stationList', stations_resp.get('data', {}).get('list', []))
        logger.info(f"Found {len(station_list)} stations in Deye Cloud")
        
        # Create a mapping of station ID to station name
        cloud_stations = {str(s.get('id')): s.get('name') for s in station_list}
        
        for device in devices:
            logger.info(f"Checking device {device.device_sn} (Local name: {device.name})")
            
            # Note: In some cases device_sn is used as station_id in the Vegriddy app
            cloud_name = cloud_stations.get(str(device.device_sn))
            
            if cloud_name:
                if cloud_name != device.name:
                    logger.warning(f"  Mismatch! Cloud name: {cloud_name}, Local name: {device.name}")
                else:
                    logger.info(f"  Match! Name: {device.name}")
            else:
                logger.warning(f"  Station ID {device.device_sn} not found in Deye Cloud station list")
                
                # Try listWithDevice as well
                with_device_resp = service.get_station_list_with_device()
                with_device_list = with_device_resp.get('stationList', with_device_resp.get('data', {}).get('list', []))
                
                found_in_device_list = False
                for station in with_device_list:
                    for d in station.get('deviceListItems', []):
                        if str(d.get('deviceSn')) == str(device.device_sn):
                            found_in_device_list = True
                            cloud_name = station.get('name')
                            if cloud_name != device.name:
                                logger.warning(f"  Mismatch in listWithDevice! Cloud name: {cloud_name}, Local name: {device.name}")
                            else:
                                logger.info(f"  Match in listWithDevice! Name: {device.name}")
                            break
                    if found_in_device_list: break
                
                if not found_in_device_list:
                    logger.warning(f"  Device SN {device.device_sn} not found in any cloud station")

    except Exception as e:
        logger.error(f"Error checking synchronization: {str(e)}")

if __name__ == "__main__":
    check_site_name_sync()
