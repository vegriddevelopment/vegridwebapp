import requests
import sys
import os

# To use Django's models, we need to set up the environment
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
import django
django.setup()

from vegrid_app.models import DeyeDevice

def test_fetch_realtime_data():
    # 1. Configuration
    # We'll pull from the first device in the database for testing
    device = DeyeDevice.objects.first()
    
    if not device:
        print("No devices found in the database. Please add one first.")
        return

    # Use the correct data center URL for your region
    # The user suggested eu1-developer.deyecloud.com
    baseurl = "https://eu1-developer.deyecloud.com/v1.0"
    
    # In a real scenario, you'd get the token via DeyeAPI().get_token()
    # For this test, we'll try to use the stored token if it's still valid
    token = device.last_token
    device_sn = device.device_sn
    
    print(f"Testing for Device SN: {device_sn}")
    
    if not token:
        print("No stored token found for this device. Please run a sync first or provide a token manually.")
        # If we wanted to be proactive, we could call device.get_token() here
        try:
            token = device.get_token()
            print("Successfully obtained a new token.")
        except Exception as e:
            print(f"Failed to obtain token: {e}")
            return

    # 2. Set Headers
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'bearer {token}'
    }

    # 3. Prepare Request Body
    data = {
        "deviceList": [device_sn]
    }

    # 4. Make API Call
    url = f"{baseurl}/device/latest"
    print(f"Calling: {url}")
    
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
                    
                    print("\n--- Real-time Data ---")
                    # Find specific interesting points
                    pv_power = next((item['value'] for item in points if item['key'] == 'totalPvPower'), "N/A")
                    today_yield = next((item['value'] for item in points if item['key'] == 'todayYield'), "N/A")
                    total_yield = next((item['value'] for item in points if item['key'] == 'totalYield'), "N/A")
                    
                    print(f"Device SN: {device_sn}")
                    print(f"Current PV Power: {pv_power} W")
                    print(f"Today Yield: {today_yield} kWh")
                    print(f"Total Yield: {total_yield} kWh")
                    
                    # Print all available points for reference
                    print("\nAll Available Measure Points:")
                    for point in points:
                        print(f"- {point['key']}: {point['value']} {point.get('unit', '')}")
                else:
                    print("No data found for this device in the response.")
            else:
                print(f"API Error (Code {result.get('code')}): {result.get('msg')}")
                print(f"Full response: {result}")
        else:
            print(f"HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    test_fetch_realtime_data()
