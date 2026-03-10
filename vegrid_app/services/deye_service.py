import time
import hashlib
import requests
import json
import logging
from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache

# OpenWeatherMap API helper function
def fetch_weather_from_openweather(lat, lon):
    """Fetch weather data from OpenWeatherMap API using latitude and longitude."""
    api_key = settings.OPENWEATHER_API_KEY
    if not api_key:
        logger.error("OpenWeatherMap API key not configured")
        return None
    
    base_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric"  # Use metric units (Celsius)
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "tmp": data.get("main", {}).get("temp"),
                "weatherName": data.get("weather", [{}])[0].get("main"),
                "weatherIcon": data.get("weather", [{}])[0].get("icon"),
                "humidity": data.get("main", {}).get("humidity"),
                "windSpeed": data.get("wind", {}).get("speed")
            }
        else:
            logger.error(f"OpenWeatherMap API error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error fetching weather from OpenWeatherMap: {str(e)}")
        return None

logger = logging.getLogger(__name__)

class DeyeServiceError(Exception):
    """Base exception for DeyeService"""
    def __init__(self, message, status_code=502):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class DeyeService:
    _instance = None
    _token = None
    _token_expiry = 0

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DeyeService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self.base_url = settings.DEYE_API_BASE_URL
        self.app_id = settings.DEYE_APP_ID
        self.app_secret = settings.DEYE_APP_SECRET
        self.username = settings.DEYE_USERNAME
        self.password = settings.DEYE_PASSWORD

    def _get_password_hash(self, password):
        """Deye Developer API requires SHA256 hashed password"""
        return hashlib.sha256(password.encode()).hexdigest().lower()

    def get_token(self):
        """Fetch or refresh access token with 60s buffer"""
        current_time = time.time()
        
        # Check in-memory cache first
        if self._token and current_time < (self._token_expiry - 60):
            return self._token

        # Check Django cache (useful if multiple workers)
        cached_token = cache.get('deye_access_token')
        cached_expiry = cache.get('deye_token_expiry', 0)
        if cached_token and current_time < (cached_expiry - 60):
            self._token = cached_token
            self._token_expiry = cached_expiry
            return cached_token

        return self._authenticate()

    def _authenticate(self):
        """Perform login and store token"""
        url = f"{self.base_url}/v1.0/account/token"
        
        # appId is required in query params
        params = {"appId": self.app_id}
        
        # Using SHA256 and 'email' as identified in testing
        payload = {
            "appSecret": self.app_secret,
            "password": self._get_password_hash(self.password),
            "email": self.username
        }

        try:
            logger.info(f"Authenticating with Deye API at {url}")
            response = requests.post(url, params=params, json=payload, timeout=10)
            result = response.json()

            # Success code is often 0 or "1000000" in Deye API responses
            if result.get('code') in [0, "0", "1000000"]:
                data = result.get('data') or result # Sometimes token is at top level
                
                # If result['success'] is true, it might be in top level (as seen in testing)
                self._token = result.get('accessToken') or data.get('accessToken')
                expires_in = result.get('expiresIn') or data.get('expiresIn') or 86400
                
                if not self._token:
                     error_msg = result.get('msg', 'Token missing in success response')
                     logger.error(f"Deye Token Missing: {error_msg}")
                     raise DeyeServiceError(f"Deye API error: {error_msg}", status_code=401)

                logger.info(f"Deye token obtained successfully: {self._token[:10]}...")
                self._token_expiry = time.time() + int(expires_in)
                
                # Update Django cache
                cache.set('deye_access_token', self._token, int(expires_in))
                cache.set('deye_token_expiry', self._token_expiry, int(expires_in))
                
                logger.info("Deye authentication successful")
                return self._token
            else:
                error_msg = result.get('msg', 'Authentication failed')
                # Parse internal error if msg is JSON string
                if isinstance(error_msg, str) and error_msg.startswith('{'):
                    try:
                        error_msg = json.loads(error_msg).get('error', error_msg)
                    except: pass
                
                logger.error(f"Deye Authentication Error: {error_msg}")
                raise DeyeServiceError(f"Deye API error: {error_msg}", status_code=401)

        except requests.exceptions.RequestException as e:
            logger.error(f"Deye API Network Error: {str(e)}")
            raise DeyeServiceError(f"Network error: {str(e)}")

    def get_account_info(self):
        """Query relationship between account and the organization it belongs to"""
        token = self.get_token()
        url = f"{self.base_url}/v1.0/account/info"
        params = {"appId": self.app_id}
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        response = requests.post(url, params=params, json={}, headers=headers)
        return response.json()

    def get_station_detail(self, device_sn):
        """Fetch real-time data for a device (station) using device/history endpoint"""
        token = self.get_token()
        
        # First, try to get device list with station info
        stations_resp = self.get_station_list_with_device()
        if stations_resp.get('code') in [0, "0", "1000000"]:
            station_list = stations_resp.get('stationList', stations_resp.get('data', {}).get('list', []))
            for station in station_list:
                # Check if this station has our device
                device_list_items = station.get('deviceListItems', [])
                for device in device_list_items:
                    if str(device.get('deviceSn')) == str(device_sn) or str(station.get('id')) == str(device_sn):
                        logger.info(f"Found device data for {device_sn} in station {station.get('name')}")
                        
                        # Try to get real-time data from history
                        data = self.get_latest_device_data(device.get('deviceSn'))
                        
                        # If history returns zeros, try station/latest for some fields
                        if data.get('pvPower') == 0:
                             latest_resp = self.get_station_latest(station.get('id'))
                             if latest_resp.get('code') in [0, "0", "1000000"]:
                                 latest_data = latest_resp.get('data', {})
                                 # generationPower is often in station/latest data too
                                 if latest_data.get('generationPower'):
                                     data['pvPower'] = float(latest_data.get('generationPower', 0)) / 1000
                        
                        # Calculate PV Self-Consumption for today (kWh)
                        # pv_self = consumption - discharge - import
                        daily_consumption = data.get('dailyConsumption', 0)
                        daily_discharge = data.get('dailyDischarge', 0)
                        daily_import = data.get('dailyGridImport', 0)
                        pv_self_consumption = daily_consumption - daily_discharge - daily_import
                        if pv_self_consumption < 0: pv_self_consumption = 0
                        
                        # Also get station detail for weather/location if not already provided
                        station_info = {}
                        detail_resp = self.get_station_detail_by_id(station.get('id'))
                        if detail_resp.get('code') in [0, "0", "1000000"]:
                            station_info = detail_resp.get('data', {})

                        return {
                            "pvPower": data.get('pvPower', 0),
                            "batterySoc": data.get('batterySoc', 0),
                            "gridPower": data.get('gridPower', 0),
                            "batteryPower": data.get('batteryPower', 0),
                            "loadPower": data.get('loadPower', 0),
                            "pv1Power": data.get('pv1Power', 0),
                            "pv2Power": data.get('pv2Power', 0),
                            "pv3Power": data.get('pv3Power', 0),
                            "pv4Power": data.get('pv4Power', 0),
                            "totalPvPower": data.get('totalPvPower', 0),
                            "dailyProduction": data.get('dailyProduction', 0),
                            "dailyConsumption": daily_consumption,
                            "dailyDischarge": daily_discharge,
                            "dailyGridImport": daily_import,
                            "pvSelfConsumption": pv_self_consumption,
                            "totalProduction": data.get('totalProduction', 0),
                            "collectionTime": data.get('collectionTime'),
                            "station_info_raw": station_info,
                            "is_fallback": False
                        }
        
        # Fallback to station list API if device/history fails
        logger.warning(f"Device/history endpoint failed for {device_sn}, falling back to station list API")
        return self.get_station_detail_fallback(device_sn)

    def get_latest_device_data(self, device_sn):
        """Fetch real-time data from /v1.0/device/latest instead of history"""
        # Ensure we have a list for the API call
        sns = [str(device_sn)]
        resp = self.get_device_latest(sns)
        
        results = {
            "batteryPower": 0.0,
            "pvPower": 0.0,
            "batterySoc": 0.0,
            "loadPower": 0.0,
            "gridPower": 0.0,
            "pv1Power": 0.0,
            "pv2Power": 0.0,
            "pv3Power": 0.0,
            "pv4Power": 0.0,
            "totalPvPower": 0.0,
            "totalProduction": 0.0,
            "collectionTime": None
        }
        
        if resp.get('code') not in [0, "0", "1000000"]:
            logger.error(f"device/latest failed for {device_sn}: {resp}")
            return results
            
        device_list = resp.get('deviceDataList', [])
        if not device_list:
            logger.warning(f"No device data found in latest response for {device_sn}")
            return results
            
        # Extract data from the first device in the list
        device_obj = device_list[0]
        results["collectionTime"] = device_obj.get("collectionTime")
        data_list = device_obj.get('dataList', [])
        for item in data_list:
            key = item.get('key')
            val_str = item.get('value', 0)
            try:
                val = float(val_str)
            except (ValueError, TypeError):
                val = 0.0
            
            if key == 'BatteryPower':
                results["batteryPower"] = val / 1000
            elif key == 'TotalDCInputPower':
                results["pvPower"] = val / 1000
                results["totalPvPower"] = val
            elif key == 'SOC':
                results["batterySoc"] = val
            elif key == 'TotalConsumptionPower':
                results["loadPower"] = val / 1000
            elif key == 'TotalGridPower':
                results["gridPower"] = val / 1000
            elif key == 'DailyActiveProduction':
                results["dailyProduction"] = val
            elif key == 'TotalActiveProduction':
                results["totalProduction"] = val
            elif key == 'DailyConsumption':
                results["dailyConsumption"] = val
            elif key == 'DailyChargingEnergy':
                results["dailyCharge"] = val
            elif key == 'DailyDischargingEnergy':
                results["dailyDischarge"] = val
            elif key == 'DailyGridFeedIn':
                results["dailyGridFeedIn"] = val
            elif key == 'DailyEnergyPurchased' or key == 'DailyGridImport':
                results["dailyGridImport"] = val
        
        logger.info(f"Real-time data for {device_sn}: {results}")
        return results
        
    def get_station_list_with_device(self, page=1, size=20, device_type="INVERTER"):
        """Get station list with device details"""
        token = self.get_token()
        url = f"{self.base_url}/v1.0/station/listWithDevice"
        params = {"appId": self.app_id}
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "page": page,
            "size": size,
            "deviceType": device_type
        }
        
        try:
            logger.info(f"Getting station list with device details from {url}")
            response = requests.post(url, params=params, json=payload, headers=headers, timeout=10)
            result = response.json()
            logger.info(f"Station list with device response: {result}")
            return result
        except Exception as e:
            logger.error(f"Error getting station list with device: {str(e)}")
            return {"code": -1, "msg": str(e)}
    
    def get_latest_battery_power(self, device_sn):
        """Get latest battery power from device history"""
        token = self.get_token()
        base_url = self.base_url
        app_id = self.app_id
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Get historical data for BatteryPower (last 10 minutes)
        url = f"{base_url}/v1.0/device/history"
        params = {"appId": app_id}
        
        end_time = timezone.now()
        start_time = end_time - timedelta(minutes=10)
        
        payload = {
            "deviceSn": device_sn,
            "measurePoints": ["BatteryPower"],
            "startAt": start_time.strftime("%Y-%m-%d"),
            "endAt": end_time.strftime("%Y-%m-%d"),
            "granularity": 1  # 5-minute intervals
        }
        
        try:
            logger.info(f"Requesting battery power history for device {device_sn}")
            response = requests.post(url, params=params, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('code') in [0, "0", "1000000"]:
                    data_list = result.get('dataList', [])
                    if data_list:
                        # Get latest data point
                        latest_data = sorted(data_list, key=lambda x: int(x['time']))[-1]
                        item_list = latest_data.get('itemList', [])
                        for item in item_list:
                            if item.get('key') == 'BatteryPower':
                                battery_power = float(item.get('value')) / 1000  # Convert to kW
                                logger.info(f"Latest battery power: {battery_power:.2f} kW")
                                return battery_power
                        
        except Exception as e:
            logger.error(f"Error getting latest battery power: {str(e)}")
        
        return 0.0
    
    def get_latest_load_power(self, device_sn):
        """Get latest load power from device history"""
        token = self.get_token()
        base_url = self.base_url
        app_id = self.app_id
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Get historical data for TotalConsumptionPower (last 10 minutes)
        url = f"{base_url}/v1.0/device/history"
        params = {"appId": app_id}
        
        end_time = timezone.now()
        start_time = end_time - timedelta(minutes=10)
        
        payload = {
            "deviceSn": device_sn,
            "measurePoints": ["TotalConsumptionPower"],
            "startAt": start_time.strftime("%Y-%m-%d"),
            "endAt": end_time.strftime("%Y-%m-%d"),
            "granularity": 1  # 5-minute intervals
        }
        
        try:
            logger.info(f"Requesting load power history for device {device_sn}")
            response = requests.post(url, params=params, json=payload, headers=headers, timeout=20)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('code') in [0, "0", "1000000"]:
                    data_list = result.get('dataList', [])
                    if data_list:
                        # Get latest data point
                        latest_data = sorted(data_list, key=lambda x: int(x['time']))[-1]
                        item_list = latest_data.get('itemList', [])
                        for item in item_list:
                            if item.get('key') == 'TotalConsumptionPower':
                                load_power = float(item.get('value')) / 1000  # Convert to kW
                                logger.info(f"Latest load power: {load_power:.2f} kW")
                                return load_power
                        
        except Exception as e:
            logger.error(f"Error getting latest load power: {str(e)}")
        
        return 0.0
    
    def get_latest_generation_power(self, device_sn):
        """Get latest generation power from device history"""
        token = self.get_token()
        base_url = self.base_url
        app_id = self.app_id
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Get historical data for TotalDCInputPower (last 10 minutes) - real-time PV power
        url = f"{base_url}/v1.0/device/history"
        params = {"appId": app_id}
        
        end_time = timezone.now()
        start_time = end_time - timedelta(minutes=10)
        
        payload = {
            "deviceSn": device_sn,
            "measurePoints": ["TotalDCInputPower"],
            "startAt": start_time.strftime("%Y-%m-%d"),
            "endAt": end_time.strftime("%Y-%m-%d"),
            "granularity": 1  # 5-minute intervals
        }
        
        try:
            logger.info(f"Requesting generation power history for device {device_sn}")
            response = requests.post(url, params=params, json=payload, headers=headers, timeout=20)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('code') in [0, "0", "1000000"]:
                    data_list = result.get('dataList', [])
                    if data_list:
                        # Get latest data point
                        latest_data = sorted(data_list, key=lambda x: int(x['time']))[-1]
                        item_list = latest_data.get('itemList', [])
                        for item in item_list:
                            if item.get('key') == 'TotalDCInputPower':
                                generation_power = float(item.get('value')) / 1000  # Convert to kW
                                logger.info(f"Latest generation power: {generation_power:.2f} kW")
                                return generation_power
                        
        except Exception as e:
            logger.error(f"Error getting latest generation power: {str(e)}")
        
        return 0.0

    def sync_site_names(self, customer=None):
        """Sync station names and location details from Deye Cloud to local DeyeDevice model.
        If customer is provided, will also create DeyeDevice objects for any new stations found.
        """
        from vegrid_app.models import DeyeDevice
        
        logger.info(f"Syncing site details from Deye Cloud... (Customer: {customer.id if customer else 'All'})")
        
        try:
            # Get station list with device details
            stations_resp = self.get_station_list_with_device()
            if stations_resp.get('code') not in [0, "0", "1000000"]:
                logger.error(f"Failed to get station list for name sync: {stations_resp.get('msg')}")
                return False
                
            station_list = stations_resp.get('stationList', stations_resp.get('data', {}).get('list', []))
            
            # Create a map of deviceSn to station details
            device_to_info = {}
            processed_station_ids = []

            for station in station_list:
                station_id = str(station.get('id'))
                processed_station_ids.append(station_id)

                info = {
                    'name': station.get('name'),
                    'lat': station.get('locationLat'),
                    'lng': station.get('locationLng'),
                    'address': station.get('locationAddress'),
                    'station_id': station_id
                }
                
                device_list = station.get('deviceListItems', [])
                for device_item in device_list:
                    sn = str(device_item.get('deviceSn'))
                    device_to_info[sn] = info
                
                # Also map station ID in case it's used as device_sn
                device_to_info[station_id] = info

                # If we have a customer, ensure this station/device exists in our DB
                if customer:
                    # Identify ALL potential device SNs for this station
                    device_sns = [str(d.get('deviceSn')) for d in device_list]
                    # Only include the station ID itself as a possible SN if there are NO other devices
                    if not device_sns and station_id:
                        device_sns.append(station_id)
                    
                    for sn in device_sns:
                        # Skip if SN is empty
                        if not sn or sn == 'None':
                            continue
                            
                        # Check if this SN exists ANYWHERE in the database
                        existing = DeyeDevice.objects.filter(device_sn=sn).first()
                        
                        if existing:
                            # If it exists, only update it if it's NOT linked to another customer
                            # or if the current customer is the same
                            if existing.customer and existing.customer != customer:
                                logger.warning(f"DeyeDevice {existing.device_sn} is already linked to customer {existing.customer.user.username}. Skipping link for {customer.user.username}.")
                                continue
                                
                            if not existing.customer:
                                existing.customer = customer
                            
                            existing.name = info['name']
                            existing.station_id = info['station_id']
                            existing.latitude = info['lat']
                            existing.longitude = info['lng']
                            existing.location_address = info['address']
                            existing.save()
                        else:
                            # Create new device entry for this SN
                            logger.info(f"Creating missing DeyeDevice for customer {customer.id}: {info['name']} (SN/ID: {sn})")
                            DeyeDevice.objects.create(
                                customer=customer,
                                name=info['name'],
                                device_sn=sn,
                                station_id=info['station_id'],
                                latitude=info['lat'],
                                longitude=info['lng'],
                                location_address=info['address']
                            )
            
            # Update existing local devices (across all customers if no customer specified)
            if customer:
                devices = DeyeDevice.objects.filter(customer=customer)
            else:
                devices = DeyeDevice.objects.all()

            updated_count = 0
            for device in devices:
                cloud_info = device_to_info.get(str(device.device_sn))
                if cloud_info:
                    updated = False
                    if device.name != cloud_info['name']:
                        logger.info(f"Updating name for device {device.device_sn}: {device.name} -> {cloud_info['name']}")
                        device.name = cloud_info['name']
                        updated = True
                    
                    if cloud_info['lat'] is not None and device.latitude != cloud_info['lat']:
                        device.latitude = cloud_info['lat']
                        updated = True
                    
                    if cloud_info['lng'] is not None and device.longitude != cloud_info['lng']:
                        device.longitude = cloud_info['lng']
                        updated = True
                        
                    if cloud_info['address'] and device.location_address != cloud_info['address']:
                        device.location_address = cloud_info['address']
                        updated = True
                    
                    if cloud_info['station_id'] and device.station_id != cloud_info['station_id']:
                        device.station_id = cloud_info['station_id']
                        updated = True
                        
                    if updated:
                        device.save()
                        updated_count += 1
            
            logger.info(f"Site detail sync completed. Updated {updated_count} devices.")
            return True
            
        except Exception as e:
            logger.error(f"Error syncing site names: {str(e)}")
            return False
    
    def get_latest_battery_soc(self, device_sn):
        """Get latest battery SOC from device history"""
        token = self.get_token()
        base_url = self.base_url
        app_id = self.app_id
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Get historical data for SOC (last 10 minutes)
        url = f"{base_url}/v1.0/device/history"
        params = {"appId": app_id}
        
        end_time = timezone.now()
        start_time = end_time - timedelta(minutes=10)
        
        payload = {
            "deviceSn": device_sn,
            "measurePoints": ["SOC"],
            "startAt": start_time.strftime("%Y-%m-%d"),
            "endAt": end_time.strftime("%Y-%m-%d"),
            "granularity": 1  # 5-minute intervals
        }
        
        try:
            logger.info(f"Requesting battery SOC history for device {device_sn}")
            response = requests.post(url, params=params, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('code') in [0, "0", "1000000"]:
                    data_list = result.get('dataList', [])
                    if data_list:
                        # Get latest data point
                        latest_data = sorted(data_list, key=lambda x: int(x['time']))[-1]
                        item_list = latest_data.get('itemList', [])
                        for item in item_list:
                            if item.get('key') == 'SOC':
                                battery_soc = float(item.get('value'))
                                logger.info(f"Latest battery SOC: {battery_soc:.1f}%")
                                return battery_soc
                        
        except Exception as e:
            logger.error(f"Error getting latest battery SOC: {str(e)}")
        
        return 0.0
    
    def get_latest_grid_power(self, device_sn):
        """Get latest grid power from device history"""
        token = self.get_token()
        base_url = self.base_url
        app_id = self.app_id
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Get historical data for TotalGridPower (last 10 minutes)
        url = f"{base_url}/v1.0/device/history"
        params = {"appId": app_id}
        
        end_time = timezone.now()
        start_time = end_time - timedelta(minutes=10)
        
        payload = {
            "deviceSn": device_sn,
            "measurePoints": ["TotalGridPower"],
            "startAt": start_time.strftime("%Y-%m-%d"),
            "endAt": end_time.strftime("%Y-%m-%d"),
            "granularity": 1  # 5-minute intervals
        }
        
        try:
            logger.info(f"Requesting grid power history for device {device_sn}")
            response = requests.post(url, params=params, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('code') in [0, "0", "1000000"]:
                    data_list = result.get('dataList', [])
                    if data_list:
                        # Get latest data point
                        latest_data = sorted(data_list, key=lambda x: int(x['time']))[-1]
                        item_list = latest_data.get('itemList', [])
                        for item in item_list:
                            if item.get('key') == 'TotalGridPower':
                                grid_power = float(item.get('value')) / 1000  # Convert to kW
                                logger.info(f"Latest grid power: {grid_power:.2f} kW")
                                return grid_power
                        
        except Exception as e:
            logger.error(f"Error getting latest grid power: {str(e)}")
        
        return 0.0
            
    def get_station_detail_fallback(self, device_sn):
        """Fallback to station list API if device/history fails"""
        token = self.get_token()
        stations_resp = self.get_station_list()
        if stations_resp.get('code') in [0, "0", "1000000"]:
            station_list = stations_resp.get('stationList', stations_resp.get('data', {}).get('list', []))
            for station in station_list:
                s_id = str(station.get('id'))
                if s_id == str(device_sn):
                    logger.info(f"Found station data for {device_sn} (fallback)")
                    
                    # Try to get latest metrics for better fallback data
                    pv_power = 0
                    battery_soc = station.get('batterySOC') or 0
                    
                    try:
                        latest_resp = self.get_station_latest(s_id)
                        if latest_resp.get('code') in [0, "0", "1000000"]:
                            latest_data = latest_resp.get('data', {})
                            pv_power = float(latest_data.get('generationPower', 0)) / 1000
                            # Update battery SOC if available in latest
                            if latest_data.get('batterySoc'):
                                battery_soc = latest_data.get('batterySoc')
                    except Exception as e:
                        logger.warning(f"Failed to get latest station metrics for fallback: {e}")
                        # Fallback to station list value if latest fails
                        pv_power = float(station.get('generationPower', 0)) / 1000
                    
                    return {
                        "pvPower": pv_power,
                        "batterySoc": battery_soc,
                        "gridPower": 0,
                        "batteryPower": 0,
                        "loadPower": 0,
                        "is_fallback": True
                    }
        
        logger.warning(f"No station found for {device_sn}")
        raise DeyeServiceError(f"Station {device_sn} not found")
    
    def get_alerts(self, device_sn=None, save_to_db=True):
        """Get real alerts from Deye Cloud and optionally save to DB"""
        from vegrid_app.deye_api import DeyeAPI
        from vegrid_app.models import Alert, DeyeDevice, Customer
        
        logger.info(f"Fetching real alerts from Deye Cloud for device: {device_sn}")
        
        api = DeyeAPI()
        token = self.get_token()
        
        alerts_list = []
        
        try:
            # If no device_sn, get all devices for the account
            devices_to_check = []
            stations_to_check = []
            
            if device_sn:
                # Check if this device_sn is actually a station_id
                # (Station IDs are usually shorter/numeric, e.g., 61776373)
                sns = self._get_device_sns_from_station_id(device_sn)
                if sns:
                    logger.info(f"Resolved station_id {device_sn} to SNs: {sns}")
                    stations_to_check.append(device_sn)
                    devices_to_check.extend(sns)
                else:
                    # It might be a device SN, try to find its station ID
                    s_id = self.get_station_id_by_device_sn(device_sn)
                    if s_id:
                        logger.info(f"Found station_id {s_id} for device_sn {device_sn}")
                        stations_to_check.append(s_id)
                    # Add original sn to check device-specific alarm endpoint too
                    devices_to_check.append(device_sn)
            else:
                # Get devices from DB or API
                stations_resp = self.get_station_list_with_device()
                if stations_resp.get('code') in [0, "0", "1000000"]:
                    station_list = stations_resp.get('stationList', stations_resp.get('data', {}).get('list', []))
                    for station in station_list:
                        s_id = station.get('id')
                        if s_id: stations_to_check.append(s_id)
                        for device in station.get('deviceListItems', []):
                            devices_to_check.append(device.get('deviceSn'))

            # 1. Try fetching station-based alarms first
            for s_id in stations_to_check:
                resp = api.get_station_alarms(token, s_id)
                # Fallback to station/alarm if /list returns 404
                if resp.get('status') == 404 or resp.get('code') == "2101019":
                    old_url = f"{api.base_url}/v1.0/station/alarm"
                    logger.info(f"Retrying station alarm with old URL: {old_url}")
                    resp = requests.post(old_url, params={"appId": api.app_id}, json={"id": s_id}, headers=api._get_headers(token)).json()

                if resp.get('code') in [0, "0", "1000000"]:
                    # Resolve station name once per station
                    station_name = self.get_station_name_by_id(s_id)
                    
                    alarms = resp.get('stationAlertItems', [])
                    for alarm in alarms:
                        # Convert Unix timestamp to readable date
                        alert_time = datetime.fromtimestamp(alarm.get('alertStartTime')).strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Build detailed message
                        description = alarm.get('description') or ""
                        reason = alarm.get('reason') or ""
                        solution = alarm.get('solution') or ""
                        raw_alert_type = alarm.get('alertName') or "N/A"
                        
                        message_parts = []
                        message_parts.append(f"Original Alert Type: {raw_alert_type}")
                        if description: message_parts.append(f"Description: {description}")
                        if reason: message_parts.append(f"Reason: {reason}")
                        if solution: message_parts.append(f"Solution: {solution}")
                        
                        full_message = "\n".join(message_parts) if message_parts else f"Alert Code: {alarm.get('alertCode', 'N/A')}"

                        alert_data = {
                            "date": alert_time,
                            "site": station_name,
                            "source": "Station",
                            "alert_type": self._format_alert_name(alarm.get('alertName')),
                            "severity": self._map_severity(alarm.get('level')),
                            "status": "Open" if alarm.get('status') == 1 else "Closed",
                            "message": full_message
                        }
                        if save_to_db:
                            # Try to find a device SN to link to, or use station ID
                            sns_for_station = self._get_device_sns_from_station_id(s_id)
                            target_sn = sns_for_station[0] if sns_for_station else s_id
                            self._save_alert_to_db(target_sn, alert_data)
                        
                        if not any(a['alert_type'] == alert_data['alert_type'] and a['date'] == alert_data['date'] for a in alerts_list):
                            alerts_list.append(alert_data)

            # 2. Try fetching device-based alarms
            for sn in devices_to_check:
                resp = api.get_device_alarms(token, sn)
                # Fallback to device/alarm if /list returns 404
                if resp.get('status') == 404 or resp.get('code') == "2101019":
                    old_url = f"{api.base_url}/v1.0/device/alarm"
                    logger.info(f"Retrying device alarm with old URL: {old_url} for {sn}")
                    try:
                        resp = requests.post(old_url, params={"appId": api.app_id}, json={"deviceSn": sn}, headers=api._get_headers(token)).json()
                    except:
                        resp = {"status": 404}

                if resp.get('code') in [0, "0", "1000000"]:
                    # Resolve station/plant name for this device
                    plant_name = self.get_station_name_by_device_sn(sn)
                    
                    alarms = resp.get('alertList', [])
                    for alarm in alarms:
                        # Convert Unix timestamp to readable date
                        alert_time = datetime.fromtimestamp(alarm.get('alertStartTime')).strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Build detailed message
                        description = alarm.get('description') or ""
                        reason = alarm.get('reason') or ""
                        solution = alarm.get('solution') or ""
                        raw_alert_type = alarm.get('alertName') or "N/A"
                        
                        message_parts = []
                        message_parts.append(f"Device SN: {sn}")
                        message_parts.append(f"Original Alert Type: {raw_alert_type}")
                        if description: message_parts.append(f"Description: {description}")
                        if reason: message_parts.append(f"Reason: {reason}")
                        if solution: message_parts.append(f"Solution: {solution}")
                        
                        full_message = "\n".join(message_parts) if message_parts else f"Alert Code: {alarm.get('alertCode', 'N/A')}"

                        alert_data = {
                            "date": alert_time,
                            "site": plant_name,
                            "source": "Inverter",
                            "alert_type": self._format_alert_name(alarm.get('alertName')),
                            "severity": self._map_severity(alarm.get('level')),
                            "status": "Open" if alarm.get('status') == 1 else "Closed",
                            "message": full_message
                        }
                        if save_to_db:
                            self._save_alert_to_db(sn, alert_data)
                        
                        if not any(a['alert_type'] == alert_data['alert_type'] and a['date'] == alert_data['date'] for a in alerts_list):
                            alerts_list.append(alert_data)
                elif (resp.get('status') == 404 or resp.get('code') == "2101019") and not alerts_list:
                    # Only log warning if we haven't found ANY alerts via other means
                    logger.warning(f"Alarm endpoint returned {resp.get('status') or resp.get('code')} for device {sn}")
                    
            # Fallback: check device status from station list
            # We always check station list to identify offline devices
            stations_resp = self.get_station_list_with_device()
            if stations_resp.get('code') in [0, "0", "1000000"]:
                station_list = stations_resp.get('stationList', stations_resp.get('data', {}).get('list', []))
                for station in station_list:
                    # Resolve plant name once for the station
                    plant_name = station.get('name', f"Station {station.get('id')}")
                    
                    for device in station.get('deviceListItems', []):
                        sn = device.get('deviceSn')
                        # Check connection status (1: Normal, 0: Offline, etc.)
                        if device.get('connectStatus') == 0:
                            alert_data = {
                                "date": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "site": plant_name,
                                "source": "Communication",
                                "alert_type": "Device Offline",
                                "severity": "High",
                                "status": "Open",
                                "message": f"Device {sn} is currently offline."
                            }
                            if save_to_db:
                                self._save_alert_to_db(sn, alert_data)
                            
                            # Only add to list if we are checking this specific SN or all
                            # Also check if it's already in alerts_list
                            if not device_sn or sn == device_sn or str(device_sn) == str(station.get('id')):
                                if not any(a['alert_type'] == "Device Offline" and a['site'].endswith(sn) for a in alerts_list):
                                    alerts_list.append(alert_data)
            
            return alerts_list
            
        except Exception as e:
            logger.error(f"Error fetching alerts from Deye API: {str(e)}")
            return []

    def _save_alert_to_db(self, sn, alert_data):
        """Helper to save alert to database with deduplication"""
        from vegrid_app.models import Alert, DeyeDevice
        try:
            logger.info(f"Saving alert to DB: {alert_data}")
            device = DeyeDevice.objects.get(device_sn=sn)
            # Check if alert already exists (deduplication)
            existing = Alert.objects.filter(
                customer=device.customer,
                alert_type=alert_data["alert_type"],
                status="Open"
            ).first()
            
            if not existing:
                alert_date = datetime.strptime(alert_data["date"], "%Y-%m-%d %H:%M:%S")
                # Make naive datetime aware if timezone support is enabled
                if timezone.is_naive(alert_date):
                    alert_date = timezone.make_aware(alert_date)
                logger.info(f"Aware alert date: {alert_date}")
                Alert.objects.create(
                    customer=device.customer,
                    site=alert_data["site"],
                    source=alert_data["source"],
                    alert_type=alert_data["alert_type"],
                    severity=alert_data["severity"],
                    status=alert_data["status"],
                    date=alert_date,
                    message=alert_data.get("message", "")
                )
                logger.info(f"Saved new alert for {sn}: {alert_data['alert_type']}")
            else:
                # Update existing alert with plant name if it was previously saved with ID/SN
                updated = False
                if existing.site != alert_data["site"]:
                    existing.site = alert_data["site"]
                    updated = True
                
                # Also ensure message is updated if we have better info now
                if alert_data.get("message") and existing.message != alert_data["message"]:
                    existing.message = alert_data["message"]
                    updated = True
                
                if updated:
                    existing.save()
                    logger.info(f"Updated existing alert {existing.id} with new data")

        except DeyeDevice.DoesNotExist:
            logger.warning(f"Device {sn} not found in DB, skipping save")
        except Exception as e:
            logger.error(f"Error saving alert: {str(e)}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            logger.error(f"Error saving alert to DB: {str(e)}")

    def _format_alert_name(self, alert_name):
        """Format specific alert names for better display as requested by user"""
        if not alert_name:
            return "Unknown Error"
        
        # User requested: F56DC_VoltLow_Fault -> LOW VOLT
        if "F56DC_VoltLow_Fault" in alert_name or alert_name == "LOW fault" or alert_name == "LOW Volt":
            return "LOW VOLT"
            
        return alert_name

    def _map_severity(self, level):
        """Map Deye alarm level to our severity levels"""
        # Adjust based on actual Deye API levels (1: Low, 2: Medium, 3: High, etc.)
        level_map = {
            1: "Low",
            2: "Medium",
            3: "High",
            4: "Critical"
        }
        return level_map.get(level, "Medium")

    def get_station_name_by_id(self, station_id):
        """Find station name for a given station ID"""
        cache_key = f'station_name_{station_id}'
        cached_name = cache.get(cache_key)
        if cached_name:
            return cached_name
            
        stations_resp = self.get_station_list_with_device()
        if stations_resp.get('code') in [0, "0", "1000000"]:
            station_list = stations_resp.get('stationList', stations_resp.get('data', {}).get('list', []))
            for station in station_list:
                if str(station.get('id')) == str(station_id):
                    name = station.get('name')
                    if name:
                        cache.set(cache_key, name, 86400)
                        return name
        return f"Station {station_id}"

    def get_station_name_by_device_sn(self, device_sn):
        """Find station name for a given device serial number"""
        cache_key = f'station_name_by_sn_{device_sn}'
        cached_name = cache.get(cache_key)
        if cached_name:
            return cached_name
            
        stations_resp = self.get_station_list_with_device()
        if stations_resp.get('code') in [0, "0", "1000000"]:
            station_list = stations_resp.get('stationList', stations_resp.get('data', {}).get('list', []))
            for station in station_list:
                for device in station.get('deviceListItems', []):
                    if str(device.get('deviceSn')) == str(device_sn):
                        name = station.get('name')
                        if name:
                            cache.set(cache_key, name, 86400)
                            return name
        return f"Site {device_sn}"

    def get_station_id_by_device_sn(self, device_sn):
        """Find station ID for a given device serial number"""
        cache_key = f'station_id_map_{device_sn}'
        cached_id = cache.get(cache_key)
        if cached_id:
            logger.info(f"Using cached station_id for {device_sn}: {cached_id}")
            return cached_id
            
        logger.info(f"Resolving station_id for {device_sn} from API...")
        stations_resp = self.get_station_list_with_device()
        if stations_resp.get('code') in [0, "0", "1000000"]:
            station_list = stations_resp.get('stationList', stations_resp.get('data', {}).get('list', []))
            logger.info(f"Found {len(station_list)} stations in listWithDevice")
            for station in station_list:
                for device in station.get('deviceListItems', []):
                    if str(device.get('deviceSn')) == str(device_sn):
                        station_id = station.get('id')
                        logger.info(f"Matched device {device_sn} to station {station_id}")
                        cache.set(cache_key, station_id, 86400) # Cache for 24h
                        return station_id
        
        # Try station/list as fallback
        logger.info(f"Falling back to station/list for {device_sn}")
        stations_resp = self.get_station_list()
        if stations_resp.get('code') in [0, "0", "1000000"]:
            station_list = stations_resp.get('stationList', stations_resp.get('data', {}).get('list', []))
            for station in station_list:
                if str(station.get('id')) == str(device_sn):
                    logger.info(f"Matched device {device_sn} to station ID {station.get('id')} in station/list")
                    return station.get('id')
                    
        return None

    def _get_device_sns_from_station_id(self, station_id):
        """Get all device serial numbers for a given station ID"""
        from vegrid_app.models import DeyeDevice
        
        cache_key = f'station_id_to_device_sns_{station_id}'
        cached_sns = cache.get(cache_key)
        if cached_sns:
            return cached_sns
            
        # 1. Try local DB first
        db_sns = list(DeyeDevice.objects.filter(models.Q(device_sn=station_id) | models.Q(station_id=station_id)).values_list('device_sn', flat=True))
        if db_sns:
            cache.set(cache_key, db_sns, 86400)
            return db_sns
            
        # 2. Try Deye Cloud API
        logger.info(f"Resolving device SNs for station {station_id} from listWithDevice...")
        sns = []
        stations_resp = self.get_station_list_with_device()
        if stations_resp.get('code') in [0, "0", "1000000"]:
            station_list = stations_resp.get('stationList', stations_resp.get('data', {}).get('list', []))
            for station in station_list:
                if str(station.get('id')) == str(station_id):
                    for device in station.get('deviceListItems', []):
                        sns.append(device.get('deviceSn'))
        
        if sns:
            cache.set(cache_key, sns, 86400) # Cache for 24h
            return sns
            
        # Fallback: if station_id looks like a device SN, return it
        if len(str(station_id)) >= 10:
            return [str(station_id)]
            
        return None

    def get_station_energy_day(self, station_id, date=None, device_sn=None):
        """Get daily energy production/consumption graphs"""
        if not date:
            date = timezone.now().strftime("%Y-%m-%d")
        token = self.get_token()
        url = f"{self.base_url}/v1.0/station/energy/day"
        params = {"appId": self.app_id}
        payload = {"id": station_id, "date": date}
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            logger.info(f"Requesting daily energy for station {station_id} on {date} (POST)")
            response = requests.post(url, params=params, json=payload, headers=headers, timeout=10)
            result = response.json()
            
            # If 404 or specific error code, try device/history fallback
            if response.status_code == 404 or result.get('status') == 404 or result.get('code') in ["2101019", "2101018"]:
                logger.info(f"404 for station energy day, falling back to device/history for station {station_id}")
                return self._get_station_energy_from_history(station_id, 'day', date, device_sn=device_sn)
            return result
        except Exception as e:
            logger.error(f"Error in get_station_energy_day: {str(e)}")
            # Even on exception, try fallback
            try: return self._get_station_energy_from_history(station_id, 'day', date, device_sn=device_sn)
            except: return {"code": -1, "msg": str(e), "status": 502}

    def _get_station_energy_from_history(self, station_id, period, date_val, device_sn=None):
        """Alternative to station/energy using device/history"""
        sns = self._get_device_sns_from_station_id(station_id)
        if not sns:
            if device_sn:
                logger.info(f"Using provided device_sn {device_sn} as fallback for history")
                sns = [device_sn]
            else:
                return {"code": -1, "msg": f"No devices found for station {station_id}", "status": 404}
        
        # We'll use the first device for simplicity, or aggregate if multiple
        target_sn = sns[0]
        
        token = self.get_token()
        url = f"{self.base_url}/v1.0/device/history"
        params = {"appId": self.app_id}
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Mapping points based on period
        granularity = 1
        if period == 'day':
            measure_points = ["TotalDCInputPower", "TotalConsumptionPower", "BatteryPower", "TotalGridPower"]
            start_date = date_val
            end_date = date_val
        elif period == 'month':
            # Use granularity 2 for daily breakdown in month view (one point per day)
            granularity = 2
            measure_points = None # Must be null for granularity > 1
            if len(date_val) == 7: # YYYY-MM
                start_date = f"{date_val}-01"
            else:
                start_date = date_val[:7] + "-01"
                
            import calendar
            dt = datetime.strptime(start_date, "%Y-%m-%d")
            last_day = calendar.monthrange(dt.year, dt.month)[1]
            end_date = f"{dt.year}-{dt.month:02d}-{last_day}"
        elif period == 'year':
            # Use granularity 3 for monthly breakdown in year view (one point per month)
            granularity = 3
            measure_points = None
            start_date = f"{date_val[:4]}-01"
            end_date = f"{date_val[:4]}-12"
        else: # lifetime
            # Use granularity 3 for monthly breakdown in lifetime view
            granularity = 3
            measure_points = None
            start_date = "2000-01"
            end_date = timezone.now().strftime("%Y-%m")
            
        payload = {
            "deviceSn": target_sn,
            "measurePoints": measure_points,
            "startAt": start_date,
            "endAt": end_date,
            "granularity": granularity
        }
        
        try:
            response = requests.post(url, params=params, json=payload, headers=headers, timeout=30)
            history_data = response.json()
            
            if history_data.get('code') not in [0, "0", "1000000"]:
                return history_data
                
            items = []
            for point in history_data.get('dataList', []):
                time_val = point.get('time', '0')
                try:
                    if isinstance(time_val, str) and '-' in time_val:
                        # Handle YYYY-MM-DD or YYYY-MM or YYYY-M
                        parts = time_val.split('-')
                        if len(parts) == 2:
                            item_date = datetime.strptime(time_val, "%Y-%m")
                        else:
                            item_date = datetime.strptime(time_val, "%Y-%m-%d")
                    else:
                        timestamp = int(time_val)
                        if timestamp > 0:
                            item_date = datetime.fromtimestamp(timestamp)
                        else:
                            continue
                except: 
                    logger.warning(f"Failed to parse time {time_val} from history data")
                    continue

                item = {
                    "time": item_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "generation": 0,
                    "pv_production": 0,
                    "consumption": 0,
                    "storage": 0,
                    "grid": 0
                }
                
                # Temp variables for formula calculation in Month/Year view
                discharge_val = 0
                charge_val = 0
                import_val = 0
                export_val = 0
                
                for val in point.get('itemList', []):
                    key = val.get('key')
                    try:
                        value = float(val.get('value', 0))
                    except: value = 0
                    
                    if period == 'day':
                        # Power (W) to interval energy (kWh)
                        energy_val = value / 12000.0 # 5-min interval
                        if key == 'TotalDCInputPower': 
                            item['generation'] = energy_val
                        elif key == 'TotalConsumptionPower': 
                            item['consumption'] = energy_val
                        elif key == 'BatteryPower': 
                            # Deye signed BatteryPower: + is Discharge, - is Charge
                            item['storage'] = energy_val
                        elif key == 'TotalGridPower': 
                            # Deye signed TotalGridPower: + is Export, - is Import
                            item['grid'] = energy_val
                    elif granularity in [2, 3]:
                        # Daily/Monthly totals from granularity 2 or 3
                        if key in ['Production', 'yield']: item['generation'] = value
                        elif key in ['Consumption', 'load']: item['consumption'] = value
                        elif key in ['DischargingCapacity', 'batteryDischarge']: discharge_val = value
                        elif key in ['ChargingCapacity', 'batteryCharge']: charge_val = value
                        elif key in ['ElectricityPurchasing', 'gridImport']: import_val = value
                        elif key in ['ElectricityExport', 'gridExport']: export_val = value
                    else:
                        # Fallback for granularity 1 if daily totals are available
                        if key == 'DailyActiveProduction': item['generation'] = value
                        elif key == 'DailyConsumption': item['consumption'] = value
                        elif key == 'DailyDischargingEnergy': discharge_val = value
                        elif key == 'DailyChargingEnergy': charge_val = value
                        elif key == 'DailyEnergyPurchased': import_val = value
                        elif key == 'DailyGridExport': export_val = value
                
                if period == 'day':
                    # Formula: Solar = Consumption - Battery + Grid
                    # Battery is Discharge(+)/Charge(-), Grid is Export(+)/Import(-)
                    item['pv_production'] = item['consumption'] - item['storage'] + item['grid']
                    # For UI display, we still want positive storage/grid components in chart? 
                    # User didn't specify chart changes, but formula must be used for 'pv_production'
                    # We'll keep storage and grid as absolute values for the chart visuals if needed, 
                    # but the requested formula uses the signed values.
                else:
                    # Net values for totals
                    item['storage'] = discharge_val - charge_val
                    item['grid'] = export_val - import_val
                    item['pv_production'] = item['consumption'] - item['storage'] + item['grid']
                
                # Final check: Solar should not be negative
                if item['pv_production'] < 0: item['pv_production'] = 0
                
                items.append(item)
            
            # If period is month and granularity 1, we need to pick the last entry of each day to get daily totals
            if period == 'month' and granularity == 1 and items:
                daily_items = {}
                for item in items:
                    day_key = item['time'][:10]
                    # DailyActiveProduction is cumulative for the day, so last value is daily total
                    if day_key not in daily_items or item['time'] > daily_items[day_key]['time']:
                        daily_items[day_key] = item
                items = sorted(daily_items.values(), key=lambda x: x['time'])

            return {
                "code": 0, "msg": "success", "success": True,
                "data": { "items": items }
            }
        except Exception as e:
            logger.error(f"Error in _get_station_energy_from_history: {str(e)}")
            raise e

    def get_station_energy_month(self, station_id, month=None, device_sn=None):
        """Get monthly energy production/consumption graphs"""
        if not month:
            month = timezone.now().strftime("%Y-%m")
        token = self.get_token()
        url = f"{self.base_url}/v1.0/station/energy/month"
        params = {"appId": self.app_id}
        payload = {"id": station_id, "month": month}
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            logger.info(f"Requesting monthly energy for station {station_id} for {month} (POST)")
            response = requests.post(url, params=params, json=payload, headers=headers, timeout=10)
            result = response.json()
            
            if response.status_code == 404 or result.get('status') == 404 or result.get('code') in ["2101019", "2101018"]:
                logger.info(f"404 for station energy month, falling back to device/history")
                return self._get_station_energy_from_history(station_id, 'month', month, device_sn=device_sn)
            return result
        except Exception as e:
            logger.error(f"Error in get_station_energy_month: {str(e)}")
            try: return self._get_station_energy_from_history(station_id, 'month', month, device_sn=device_sn)
            except: return {"code": -1, "msg": str(e), "status": 502}
    
    def get_station_energy_year(self, station_id, year=None, device_sn=None):
        """Get yearly energy production/consumption graphs"""
        if not year:
            year = timezone.now().strftime("%Y")
        token = self.get_token()
        url = f"{self.base_url}/v1.0/station/energy/year"
        params = {"appId": self.app_id}
        payload = {"id": station_id, "year": year}
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            logger.info(f"Requesting yearly energy for station {station_id} for {year} (POST)")
            response = requests.post(url, params=params, json=payload, headers=headers, timeout=10)
            result = response.json()
            
            if response.status_code == 404 or result.get('status') == 404 or result.get('code') in ["2101019", "2101018"]:
                logger.info(f"404 for station energy year, falling back to device/history")
                return self._get_station_energy_from_history(station_id, 'year', f"{year}-01-01", device_sn=device_sn)
            return result
        except Exception as e:
            logger.error(f"Error in get_station_energy_year: {str(e)}")
            try: return self._get_station_energy_from_history(station_id, 'year', f"{year}-01-01", device_sn=device_sn)
            except: return {"code": -1, "msg": str(e), "status": 502}
    
    def get_station_energy_lifetime(self, station_id, device_sn=None):
        """Get lifetime energy production/consumption graphs"""
        token = self.get_token()
        url = f"{self.base_url}/v1.0/station/energy/lifetime"
        params = {"appId": self.app_id}
        payload = {"id": station_id}
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            logger.info(f"Requesting lifetime energy for station {station_id} (POST)")
            response = requests.post(url, params=params, json=payload, headers=headers, timeout=10)
            result = response.json()
            
            if response.status_code == 404 or result.get('status') == 404 or result.get('code') in ["2101019", "2101018"]:
                logger.info(f"404 for station energy lifetime, falling back to device/history")
                return self._get_station_energy_from_history(station_id, 'lifetime', None, device_sn=device_sn)
            return result
        except Exception as e:
            logger.error(f"Error in get_station_energy_lifetime: {str(e)}")
            try: return self._get_station_energy_from_history(station_id, 'lifetime', None, device_sn=device_sn)
            except: return {"code": -1, "msg": str(e), "status": 502}

    def get_station_list(self, page=1, size=20):
        """Get list of stations with potential device info"""
        token = self.get_token()
        url = f"{self.base_url}/v1.0/station/list"
        # Some Deye versions support extra params to include devices
        params = {
            "appId": self.app_id, 
            "page": page, 
            "size": size,
            "includeDevice": "true",
            "includeDevices": "true"
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {"page": page, "size": size}
        response = requests.post(url, params=params, json=payload, headers=headers)
        return response.json()

    def get_station_detail_by_id(self, station_id):
        """Get detail for a specific station (not device)"""
        token = self.get_token()
        url = f"{self.base_url}/v1.0/station/detail"
        params = {"appId": self.app_id, "id": station_id}
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        response = requests.get(url, params=params, headers=headers)
        result = response.json()
        
        # If station detail endpoint fails or returns no weather data, try to get location from station list and use OpenWeatherMap
        if result.get('status') == 404 or result.get('code') in ["2101019", "2101018"] or 'data' not in result or not result.get('data'):
            logger.warning(f"Station detail endpoint failed for {station_id}, trying to get location from station list")
            
            # 1. Try get_station_list_with_device first (usually more accurate)
            list_with_dev = self.get_station_list_with_device()
            stations = []
            if list_with_dev.get('code') in [0, "0", "1000000"]:
                stations = list_with_dev.get('stationList', list_with_dev.get('data', {}).get('list', []))
            
            # 2. Try standard station/list as fallback
            if not stations:
                list_url = f"{self.base_url}/v1.0/station/list"
                list_params = {"appId": self.app_id, "page": 1, "size": 100}
                list_payload = {"page": 1, "size": 100}
                try:
                    list_response = requests.post(list_url, params=list_params, json=list_payload, headers=headers, timeout=10)
                    list_result = list_response.json()
                    if list_result.get('code') in [0, "0", "1000000"]:
                        stations = list_result.get('stationList', list_result.get('data', {}).get('list', []))
                except Exception as e:
                    logger.error(f"Error in station/list fallback: {e}")

            # Process found stations
            for station in stations:
                if str(station.get('id')) == str(station_id):
                    lat = station.get('locationLat') or station.get('lat')
                    lon = station.get('locationLng') or station.get('lng')
                    
                    data = {
                        "locationLat": lat,
                        "locationLng": lon,
                        "locationAddress": station.get('locationAddress') or station.get('address'),
                        "address": station.get('locationAddress') or station.get('address'),
                        "regionTimezone": station.get('regionTimezone') or station.get('timezone', '3'),
                        "timezone": station.get('regionTimezone') or station.get('timezone', '3'),
                        "name": station.get('name')
                    }
                    
                    if lat and lon:
                        logger.info(f"Using OpenWeatherMap to fetch weather for station {station_id} at lat: {lat}, lon: {lon}")
                        weather_data = fetch_weather_from_openweather(lat, lon)
                        if weather_data:
                            data.update(weather_data)
                            # Map OpenWeather fields to Deye expected fields if needed
                            if 'temp' in weather_data: data['tmp'] = weather_data['temp']
                            if 'weather' in weather_data: data['weatherName'] = weather_data['weather']
                    
                    result = {
                        "code": "1000000",
                        "msg": "success",
                        "success": True,
                        "data": data
                    }
                    break
        
        return result

    def get_station_devices(self, station_id):
        """Get list of devices for a specific station"""
        token = self.get_token()
        url = f"{self.base_url}/v1.0/station/device/list"
        params = {"appId": self.app_id, "stationId": station_id}
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        try:
            # Try GET first
            response = requests.get(url, params=params, headers=headers, timeout=10)
            result = response.json()
            if result.get('status') == 404 or result.get('code') == "2101019":
                # Try POST
                payload = {"stationId": station_id}
                response = requests.post(url, params={"appId": self.app_id}, json=payload, headers=headers, timeout=10)
                return response.json()
            return result
        except Exception as e:
            return {"code": -1, "msg": str(e)}

    def get_device_list(self, page=1, size=20):
        """Get list of devices"""
        token = self.get_token()
        url = f"{self.base_url}/v1.0/device/list"
        
        # appId is often required in query params for all requests
        params = {"appId": self.app_id, "page": page, "size": size}
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            # Trying GET first, then POST if it fails
            response = requests.get(url, params=params, headers=headers, timeout=10)
            result = response.json()
            if result.get('code') in [0, "0", "1000000"]:
                return result
            
            # If GET failed or returned error, try POST
            payload = {"page": page, "size": size}
            response = requests.post(url, params={"appId": self.app_id}, json=payload, headers=headers, timeout=10)
            return response.json()
        except Exception as e:
            logger.error(f"Deye API Network Error: {str(e)}")
            return {"code": -1, "msg": str(e)}

    def cleanup_alert_names(self):
        """Bulk update existing alerts with correct plant names and formatted alert types"""
        from vegrid_app.models import Alert
        logger.info("Starting bulk cleanup of alerts...")
        
        # 1. Build name map
        name_map = {} # ID/SN -> Name
        try:
            stations_resp = self.get_station_list_with_device()
            if stations_resp.get('code') in [0, "0", "1000000"]:
                station_list = stations_resp.get('stationList', stations_resp.get('data', {}).get('list', []))
                for station in station_list:
                    s_id = str(station.get('id'))
                    s_name = station.get('name')
                    if s_id and s_name:
                        name_map[f"Station {s_id}"] = s_name
                        name_map[s_id] = s_name
                    
                    for device in station.get('deviceListItems', []):
                        sn = str(device.get('deviceSn'))
                        if sn and s_name:
                            name_map[f"Site {sn}"] = s_name
                            name_map[sn] = s_name
        except Exception as e:
            logger.warning(f"Could not fetch station list for name mapping: {str(e)}")
            
        # 2. Update alerts
        count = 0
        alerts = Alert.objects.all() # Process ALL alerts to fix historical data
        for alert in alerts:
            updated = False
            
            # Fix site name
            if alert.site in name_map:
                new_site = name_map[alert.site]
                if alert.site != new_site:
                    alert.site = new_site
                    updated = True
            
            # Fix alert type (User requested: F56DC_VoltLow_Fault -> LOW fault)
            old_type = alert.alert_type
            new_type = self._format_alert_name(old_type)
            if old_type != new_type:
                # Add original type to message if it wasn't already one of the simplified types
                if old_type not in ["LOW VOLT", "LOW fault", "LOW Volt", "Unknown Error"]:
                    raw_info = f"Original Alert Type: {old_type}"
                    if not alert.message:
                        alert.message = raw_info
                    elif raw_info not in alert.message:
                        alert.message = f"{raw_info}\n{alert.message}"
                
                alert.alert_type = new_type
                updated = True
                
            if updated:
                alert.save()
                count += 1
                logger.info(f"Fixed alert {alert.id}: Type={old_type}->{new_type}, Site={alert.site}")
        
        logger.info(f"Cleanup finished. Updated {count} alerts.")
        return count

    def get_device_latest(self, device_sns):
        """Fetch latest data for a list of devices (can include weather sensors)"""
        from vegrid_app.deye_api import DeyeAPI
        api = DeyeAPI()
        token = self.get_token()
        return api.get_device_latest(token, device_sns)

    def get_device_measure_points(self, device_sn):
        """Fetch all supported measure points for a device"""
        from vegrid_app.deye_api import DeyeAPI
        api = DeyeAPI()
        token = self.get_token()
        return api.get_device_measure_points(token, device_sn)

    def get_station_latest(self, station_id):
        """Fetch latest aggregated data for a station including generationToday"""
        from vegrid_app.deye_api import DeyeAPI
        api = DeyeAPI()
        token = self.get_token()
        
        # 1. Try station/latest first
        resp = api.get_station_latest(token, station_id)
        
        if resp.get('code') in [0, "0", "1000000"]:
            data = resp.get('data')
            if not isinstance(data, dict):
                data = {}
                resp['data'] = data
                
            # If generationToday is missing or 0, OR we want to ensure we have latest collectionTime
            # (Always try aggregation if possible to get accurate device-synced time)
            device_agg = self._aggregate_device_latest_for_station(station_id)
            if device_agg:
                data['collectionTime'] = device_agg.get('collectionTime')
                if not data.get('generationToday') or float(data.get('generationToday')) == 0:
                    logger.info(f"Station {station_id} returned no generationToday, using device/latest aggregation...")
                    data['generationToday'] = device_agg.get('generationToday', 0)
                    data['generationTotal'] = device_agg.get('generationTotal', 0)
                    data['batteryDischargeToday'] = device_agg.get('batteryDischargeToday', 0)
                    data['consumptionToday'] = device_agg.get('consumptionToday', 0)
                    data['gridToday'] = device_agg.get('gridToday', 0)
                    data['solarProductionToday'] = device_agg.get('solarProductionToday', 0)
            return resp
            
        # 2. If station/latest fails, aggregate from device/latest
        logger.warning(f"station/latest failed for {station_id}, aggregating from device/latest")
        device_agg = self._aggregate_device_latest_for_station(station_id)
        if device_agg:
            return {
                "code": 0, "msg": "success", "success": True,
                "data": {
                    "stationId": station_id,
                    "generationToday": device_agg.get('generationToday', 0),
                    "generationTotal": device_agg.get('generationTotal', 0),
                    "batteryDischargeToday": device_agg.get('batteryDischargeToday', 0),
                    "consumptionToday": device_agg.get('consumptionToday', 0),
                    "gridToday": device_agg.get('gridToday', 0),
                    "solarProductionToday": device_agg.get('solarProductionToday', 0),
                    "collectionTime": device_agg.get('collectionTime')
                }
            }
            
        return resp

    def _aggregate_device_latest_for_station(self, station_id):
        """Helper to sum generation data from all devices in a station"""
        sns = self._get_device_sns_from_station_id(station_id)
        logger.info(f"Aggregating for station {station_id}, resolved SNS: {sns}")
        if not sns:
            return None
            
        resp = self.get_device_latest(sns)
        if resp.get('code') not in [0, "0", "1000000"]:
            logger.error(f"device/latest failed for aggregation: {resp}")
            return None
            
        total_today = 0.0
        total_lifetime = 0.0
        total_discharge_today = 0.0
        total_consumption_today = 0.0
        total_grid_today = 0.0
        total_solar_today = 0.0
        max_collection_time = None
        found = False
        
        device_data_list = resp.get('deviceDataList', [])
        logger.info(f"Found {len(device_data_list)} devices in latest response")
        
        for dev in device_data_list:
            c_time = dev.get('collectionTime')
            if c_time:
                try:
                    c_time_int = int(c_time)
                    if max_collection_time is None or c_time_int > int(max_collection_time):
                        max_collection_time = c_time
                except (ValueError, TypeError):
                    pass

            for item in dev.get('dataList', []):
                key = item.get('key')
                val_str = item.get('value')
                if val_str is None: continue
                
                try:
                    val = float(val_str)
                except (ValueError, TypeError):
                    continue
                
                if key == 'DailyActiveProduction':
                    total_today += val
                    found = True
                elif key == 'TotalActiveProduction':
                    total_lifetime += val
                    found = True
                elif key == 'DailyDischargingEnergy':
                    total_discharge_today += val
                    found = True
                elif key == 'DailyConsumption':
                    total_consumption_today += val
                    found = True
                elif key == 'DailyEnergyPurchased':
                    total_grid_today += val
                    found = True
                elif key == 'DailySolarEnergy':
                    total_solar_today += val
                    found = True
                    
        result = {
            "generationToday": total_today, 
            "generationTotal": total_lifetime,
            "batteryDischargeToday": total_discharge_today,
            "consumptionToday": total_consumption_today,
            "gridToday": total_grid_today,
            "solarProductionToday": total_solar_today,
            "collectionTime": max_collection_time
        } if found else None
        logger.info(f"Aggregation result for {station_id}: {result}")
        return result

    def sync_all_realtime_data(self):
        """Sync real-time data for all stations and update DeyeDevice model"""
        from vegrid_app.models import DeyeDevice
        
        # Fetch station list once to avoid repeated calls
        stations_resp = self.get_station_list_with_device(size=100)
        station_list = []
        if stations_resp.get('code') in [0, "0", "1000000"]:
            station_list = stations_resp.get('stationList', stations_resp.get('data', {}).get('list', []))
        
        devices = DeyeDevice.objects.all()
        success_count = 0
        
        for device in devices:
            try:
                # Find which station this device belongs to from our pre-fetched list
                target_station = None
                for station in station_list:
                    device_sns = [str(d.get('deviceSn')) for d in station.get('deviceListItems', [])]
                    if str(device.device_sn) in device_sns or str(station.get('id')) == str(device.device_sn):
                        target_station = station
                        break
                
                # Get raw data using the most direct method
                # 1. Try device/latest directly
                data = self.get_latest_device_data(device.device_sn)
                
                # 2. If all zeros, try station/latest if we found a station
                if data.get('pvPower') == 0 and data.get('loadPower') == 0 and target_station:
                    latest_resp = self.get_station_latest(target_station.get('id'))
                    if latest_resp.get('code') in [0, "0", "1000000"]:
                        l_data = latest_resp.get('data', {})
                        # Map station fields if available
                        if l_data.get('pvPower') or l_data.get('generationPower'):
                            data['pvPower'] = float(l_data.get('pvPower') or l_data.get('generationPower', 0)) / 1000
                        if l_data.get('loadPower') or l_data.get('consumptionPower'):
                            data['loadPower'] = float(l_data.get('loadPower') or l_data.get('consumptionPower', 0)) / 1000
                        if l_data.get('gridPower'):
                            data['gridPower'] = float(l_data.get('gridPower', 0)) / 1000
                        if l_data.get('batteryPower'):
                            data['batteryPower'] = float(l_data.get('batteryPower', 0)) / 1000
                        if l_data.get('soc'):
                            data['batterySoc'] = float(l_data.get('soc', 0))
                        if l_data.get('generationToday'):
                            data['dailyProduction'] = float(l_data.get('generationToday'))
                        if l_data.get('consumptionToday'):
                            data['dailyConsumption'] = float(l_data.get('consumptionToday'))

                # Map to model
                device.generation = float(data.get('pvPower', 0))
                device.load = float(data.get('loadPower', 0))
                
                # Grid power
                grid_p = float(data.get('gridPower', 0))
                if grid_p >= 0:
                    device.grid_imports = grid_p
                    device.grid_export = 0
                else:
                    device.grid_imports = 0
                    device.grid_export = abs(grid_p)
                    
                # Battery power
                device.storage = float(data.get('batteryPower', 0))
                device.battery_soc = float(data.get('batterySoc', 0))
                
                # Totals
                device.today_generation = float(data.get('dailyProduction', device.today_generation))
                device.total_generation = float(data.get('totalProduction', device.total_generation))
                device.today_consumption = float(data.get('dailyConsumption', device.today_consumption))
                
                # Online status from station list if found
                if target_station:
                    device.status = "Online" if str(target_station.get('status')) in [1, "1", "Online"] else "Offline"
                
                device.save()
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to sync device {device.device_sn}: {e}")
                
        return success_count > 0

    # Removed duplicate _get_device_sns_from_station_id


