import requests

# 1. Configuration
# Use the correct data center URL for your region
# Recommended URL: https://eu1-developer.deyecloud.com/v1.0
baseurl = "https://eu1-developer.deyecloud.com/v1.0"
token = 'YOUR_ACCESS_TOKEN'  # Replace with your actual token
device_sn = 'YOUR_DEVICE_SN' # Replace with your inverter serial number

# 2. Set Headers
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'bearer ' + token
}

# 3. Prepare Request Body
data = {
    "deviceList": [device_sn]
}

# 4. Make API Call
url = f"{baseurl}/device/latest"
print(f"Requesting data for {device_sn} from {url}...")

try:
    response = requests.post(url, headers=headers, json=data)

    # 5. Handle Response
    if response.status_code == 200:
        result = response.json()
        if result.get('code') == 200 or result.get('code') == 0:
            # Extract the data list
            device_data = result.get('data', [])
            if device_data:
                # The data is usually in a list of measure points
                points = device_data[0].get('dataList', [])
                
                # Find totalPvPower
                pv_power = next((item['value'] for item in points if item['key'] == 'totalPvPower'), "N/A")
                
                print(f"Device SN: {device_sn}")
                print(f"Current PV Power: {pv_power} W")
                
                # Print other key data points
                today_yield = next((item['value'] for item in points if item['key'] == 'todayYield'), "N/A")
                total_yield = next((item['value'] for item in points if item['key'] == 'totalYield'), "N/A")
                print(f"Today Yield: {today_yield} kWh")
                print(f"Total Yield: {total_yield} kWh")
                
                # Print all available keys for reference
                print("\nAll Available Keys:")
                for item in points:
                    print(f"- {item['key']}: {item['value']}")
            else:
                print("No data found for this device.")
        else:
            print(f"API Error: {result.get('msg')} (Code: {result.get('code')})")
            print(f"Full Response: {result}")
    else:
        print(f"HTTP Error: {response.status_code}")
        print(f"Response Body: {response.text}")
except Exception as e:
    print(f"Connection Error: {e}")
