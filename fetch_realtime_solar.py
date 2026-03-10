import requests

# 1. Configuration
# Use the correct data center URL for your region
baseurl = "https://eu1-developer.deyecloud.com/v1.0"
token = 'YOUR_ACCESS_TOKEN'  # Replace with your actual token
device_sn = 'YOUR_DEVICE_SN' # Replace with your inverter serial number

# 2. Set Headers
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'bearer ' + token
}

# 3. Request Body
data = {
    "deviceList": [device_sn]
}

# 4. Fetch Data
print(f"Requesting real-time data for {device_sn} from {baseurl}/device/latest...")

try:
    response = requests.post(f"{baseurl}/device/latest", headers=headers, json=data)
    
    if response.status_code == 200:
        result = response.json()
        
        # Check API response code
        if result.get('code') in [200, 0, "0", "1000000"]:
            # The data is returned in a list under 'data'
            data_list = result.get('data', [])
            
            if data_list:
                device_data = data_list[0]
                
                # Extracting specific PV and Consumption fields as per user snippet
                # Note: Some Deye API versions might return these inside a 'dataList' 
                # but we'll try the direct access first as requested.
                pv_power = device_data.get('totalPvPower')
                load_power = device_data.get('loadPower')
                
                # If they are None, it might be in 'dataList' - we'll check just in case
                if pv_power is None and 'dataList' in device_data:
                    points = device_data.get('dataList', [])
                    pv_power = next((item['value'] for item in points if item['key'] == 'totalPvPower'), "N/A")
                    load_power = next((item['value'] for item in points if item['key'] == 'loadPower'), "N/A")

                print(f"\n--- Real-time Solar Data ---")
                print(f"Device SN: {device_sn}")
                print(f"Current Solar Generation (PV): {pv_power} W")
                print(f"Current Home Consumption (Load): {load_power} W")
                
                # Optional: print all fields for discovery
                print("\nFull Device Data returned:")
                import json
                print(json.dumps(device_data, indent=2))
            else:
                print("No data found for this device in the response.")
        else:
            print(f"API Error: {result.get('msg')} (Code: {result.get('code')})")
            print(f"Full response: {result}")
    else:
        print(f"HTTP Error: {response.status_code} - {response.text}")
        
except Exception as e:
    print(f"An error occurred: {e}")
