import requests
import hashlib
import json
from django.conf import settings

class DeyeAPI:
    def __init__(self):
        self.base_url = settings.DEYE_API_BASE_URL
        self.app_id = settings.DEYE_APP_ID
        self.app_secret = settings.DEYE_APP_SECRET

    def _get_headers(self, token=None):
        headers = {
            'Content-Type': 'application/json'
        }
        if token:
            # Authorization header should be 'bearer {token}' as per sample curl
            headers['Authorization'] = f'bearer {token}'
        return headers

    def get_token(self, username=None, password=None, email=None, mobile=None, country_code=None, company_id=None, hash_type='sha256'):
        """
        Obtain token from /v1.0/account/token
        """
        url = f"{self.base_url}/v1.0/account/token"
        
        # Hash password based on hash_type
        if hash_type == 'sha256':
            password_hash = hashlib.sha256(password.encode()).hexdigest().lower()
        elif hash_type == 'md5':
            password_hash = hashlib.md5(password.encode()).hexdigest().lower()
        else:
            password_hash = password # raw/already hashed
        
        payload = {
            "appSecret": self.app_secret,
            "password": password_hash
        }
        
        if username: payload["username"] = username
        if email: payload["email"] = email
        if mobile: payload["mobile"] = mobile
        if country_code: payload["countryCode"] = country_code
        if company_id: payload["companyId"] = company_id

        # Use appId in params as per standard docs
        params = {"appId": self.app_id}
        
        print(f"Requesting token from {url} with appId {self.app_id}")
        
        response = requests.post(url, params=params, json=payload, headers=self._get_headers())
        return response.json()

    def get_account_info(self, token):
        """
        Query relationship between account and the organization it belongs to
        """
        url = f"{self.base_url}/v1.0/account/info"
        params = {"appId": self.app_id}
        response = requests.post(url, params=params, headers=self._get_headers(token), json={})
        return response.json()

    def get_battery_config(self, token, device_sn):
        """
        Obtain battery-related parameter value
        """
        url = f"{self.base_url}/v1.0/config/battery"
        params = {"appId": self.app_id}
        payload = {"deviceSn": device_sn}
        response = requests.post(url, params=params, json=payload, headers=self._get_headers(token))
        return response.json()

    def get_system_config(self, token, device_sn):
        """
        Obtain system work mode related parameter value
        """
        url = f"{self.base_url}/v1.0/config/system"
        params = {"appId": self.app_id}
        payload = {"deviceSn": device_sn}
        response = requests.post(url, params=params, json=payload, headers=self._get_headers(token))
        return response.json()

    def get_tou_config(self, token, device_sn):
        """
        Obtain time of use configuration
        """
        url = f"{self.base_url}/v1.0/config/tou"
        params = {"appId": self.app_id}
        payload = {"deviceSn": device_sn}
        response = requests.post(url, params=params, json=payload, headers=self._get_headers(token))
        return response.json()

    def control_battery_mode(self, token, device_sn, battery_mode_type, action="on"):
        """
        Enable or disable the chargeMode
        batteryModeType: GRID_CHARGE; GEN_CHARGE
        action: on/off
        """
        url = f"{self.base_url}/v1.0/order/battery/modeControl"
        params = {"appId": self.app_id}
        payload = {
            "action": action,
            "batteryModeType": battery_mode_type,
            "deviceSn": device_sn
        }
        response = requests.post(url, params=params, json=payload, headers=self._get_headers(token))
        return response.json()

    def update_battery_parameter(self, token, device_sn, parameter_type, value):
        """
        Set the value of battery-related parameter
        parameterType: MAX_CHARGE_CURRENT, MAX_DISCHARGE_CURRENT, GRID_CHARGE_AMPERE, BATT_LOW
        """
        url = f"{self.base_url}/v1.0/order/battery/parameter/update"
        params = {"appId": self.app_id}
        payload = {
            "deviceSn": device_sn,
            "parameterType": parameter_type,
            "value": value
        }
        response = requests.post(url, params=params, json=payload, headers=self._get_headers(token))
        return response.json()

    def update_tou_config(self, token, device_sn, time_use_setting_items, timeout_seconds=30):
        """
        Set Time of Use of the Device
        """
        url = f"{self.base_url}/v1.0/order/sys/tou/update"
        params = {"appId": self.app_id}
        payload = {
            "deviceSn": device_sn,
            "timeUseSettingItems": time_use_setting_items,
            "timeoutSeconds": timeout_seconds
        }
        response = requests.post(url, params=params, json=payload, headers=self._get_headers(token))
        return response.json()

    def get_order_status(self, token, order_id):
        """
        Obtain the command result based on orderId
        """
        url = f"{self.base_url}/v1.0/order/{order_id}"
        params = {"appId": self.app_id}
        response = requests.get(url, params=params, headers=self._get_headers(token))
        return response.json()

    def get_device_alarms(self, token, device_sn, page=1, size=20):
        """
        Obtain device alarms
        """
        url = f"{self.base_url}/v1.0/device/alertList"
        params = {"appId": self.app_id}
        # Get last 30 days of alerts (maximum allowed range)
        import time
        end_time = int(time.time())
        start_time = end_time - (30 * 24 * 3600)
        payload = {"deviceSn": device_sn, "startTimestamp": start_time, "endTimestamp": end_time}
        response = requests.post(url, params=params, json=payload, headers=self._get_headers(token))
        return response.json()

    def get_station_alarms(self, token, station_id, page=1, size=20):
        """
        Obtain station alarms
        """
        url = f"{self.base_url}/v1.0/station/alertList"
        params = {"appId": self.app_id}
        # Get last 180 days of alerts (maximum allowed range)
        import time
        end_time = int(time.time())
        start_time = end_time - (180 * 24 * 3600)
        payload = {"stationId": str(station_id), "startTimestamp": start_time, "endTimestamp": end_time, "page": page, "size": size}
        response = requests.post(url, params=params, json=payload, headers=self._get_headers(token))
        return response.json()

    def get_device_realtime(self, token, device_sn):
        """
        Obtain real-time device data
        """
        url = f"{self.base_url}/v1.0/device/realtime"
        params = {"appId": self.app_id}
        payload = {"deviceSn": device_sn}
        response = requests.post(url, params=params, json=payload, headers=self._get_headers(token))
        return response.json()

    def get_device_list(self, token, page=1, size=20):
        """
        Obtain list of devices for the account
        """
        url = f"{self.base_url}/v1.0/device/list"
        params = {"appId": self.app_id}
        payload = {"page": page, "size": size}
        response = requests.post(url, params=params, json=payload, headers=self._get_headers(token))
        return response.json()

    def get_device_latest(self, token, device_sns):
        """
        Obtain latest data for a list of device serial numbers
        """
        url = f"{self.base_url}/v1.0/device/latest"
        params = {"appId": self.app_id}
        payload = {"deviceList": device_sns}
        response = requests.post(url, params=params, json=payload, headers=self._get_headers(token))
        return response.json()

    def get_device_measure_points(self, token, device_sn):
        """
        Obtain all measure points for a specific device
        """
        url = f"{self.base_url}/v1.0/device/measurePoints"
        params = {"appId": self.app_id}
        payload = {"deviceSn": device_sn}
        response = requests.post(url, params=params, json=payload, headers=self._get_headers(token))
        return response.json()

    def get_device_history(self, token, device_sn, measure_points, start_date, end_date, granularity=1):
        """
        Obtain historical data for specific measure points
        """
        url = f"{self.base_url}/v1.0/device/history"
        params = {"appId": self.app_id}
        payload = {
            "deviceSn": device_sn,
            "measurePoints": measure_points,
            "startAt": start_date,
            "endAt": end_date,
            "granularity": granularity
        }
        response = requests.post(url, params=params, json=payload, headers=self._get_headers(token))
        return response.json()

    def get_station_latest(self, token, station_id):
        """
        Obtain latest data for a specific station
        """
        url = f"{self.base_url}/v1.0/station/latest"
        params = {
            "appId": self.app_id
        }
        payload = {
            "stationId": str(station_id)
        }
        response = requests.post(url, params=params, json=payload, headers=self._get_headers(token))
        return response.json()
