import os
import django
import json
from dotenv import load_dotenv

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
load_dotenv(override=True)
django.setup()

from vegrid_app.services.deye_service import DeyeService
from vegrid_app.deye_api import DeyeAPI

def pull_utilization_data():
    service = DeyeService()
    api = DeyeAPI()
    
    print(f"Authenticating for {service.username}...")
    token = service.get_token()
    
    if not token:
        print("Failed to obtain token")
        return

    # Get station and device
    stations_resp = service.get_station_list_with_device()
    station_list = stations_resp.get('stationList', stations_resp.get('data', {}).get('list', []))
    
    if not station_list:
        print("No stations found.")
        return

    # Find the non-demo device SN
    device_sn = None
    for station in station_list:
        station_name = station.get('name', '').lower()
        if 'demo' in station_name:
            continue
            
        device_list_items = station.get('deviceListItems', [])
        if device_list_items:
            device_sn = device_list_items[0].get('deviceSn')
            print(f"Using device: {device_sn} from station '{station.get('name')}'")
            break
    
    if not device_sn:
        print("No non-demo devices found. Falling back to the first available device.")
        for station in station_list:
            device_list_items = station.get('deviceListItems', [])
            if device_list_items:
                device_sn = device_list_items[0].get('deviceSn')
                print(f"Using device: {device_sn} from station '{station.get('name')}'")
                break
    
    if not device_sn:
        print("No devices found.")
        return

    # Pull latest data
    print(f"Pulling real-time utilization data...")
    latest_data = api.get_device_latest(token, [device_sn])
    
    if latest_data.get('code') not in [0, "0", "1000000"]:
        print(f"Failed to get data: {latest_data.get('msg')}")
        return

    device_list = latest_data.get('deviceDataList', [])
    if not device_list:
        print("No device data found in response.")
        return

    data_list = device_list[0].get('dataList', [])
    
    # Initialize metrics
    metrics = {
        'PV Power': 0.0,
        'Battery Discharge Power': 0.0,
        'Battery Charge Power': 0.0,
        'Grid Import Power': 0.0,
        'Grid Export Power': 0.0,
        'Total Consumption Power': 0.0,
        # Daily Totals (kWh)
        'Today PV': 0.0,
        'Today Discharge': 0.0,
        'Today Import': 0.0,
        'Today Consumption': 0.0
    }

    # Extract raw values
    raw_values = {}
    for item in data_list:
        raw_values[item.get('key')] = float(item.get('value', 0))

    # --- REAL-TIME POWER (W) ---
    metrics['PV Power'] = raw_values.get('TotalSolarPower', 0.0)
    
    batt_pwr = raw_values.get('BatteryPower', 0.0)
    if batt_pwr < 0:
        metrics['Battery Discharge Power'] = abs(batt_pwr)
    else:
        metrics['Battery Charge Power'] = batt_pwr

    grid_pwr = raw_values.get('TotalGridPower', 0.0)
    if grid_pwr > 0:
        metrics['Grid Import Power'] = grid_pwr
    else:
        metrics['Grid Export Power'] = abs(grid_pwr)

    metrics['Total Consumption Power'] = raw_values.get('TotalConsumptionPower', 0.0)

    # --- TODAY'S TOTALS (kWh) ---
    daily_pv_total = raw_values.get('DailyActiveProduction', 0.0)
    daily_export = raw_values.get('DailyGridFeedIn', 0.0)
    daily_import = raw_values.get('DailyEnergyPurchased', raw_values.get('DailyGridImport', 0.0))
    daily_discharge = raw_values.get('DailyDischargingEnergy', 0.0)
    daily_consumption = raw_values.get('DailyConsumption', 0.0)
    
    # Deye App "Utilization" section logic often follows:
    # Consumption = PV_Self + Discharge + Import
    # Therefore: PV_Self = Consumption - Discharge - Import
    pv_self_calc = daily_consumption - daily_discharge - daily_import
    
    metrics['Today PV'] = pv_self_calc if pv_self_calc > 0 else (daily_pv_total - daily_export)
    metrics['Today Discharge'] = daily_discharge
    metrics['Today Import'] = daily_import
    metrics['Today Consumption'] = daily_consumption

    # Display results
    print("\n" + "="*45)
    print("      DEYE UTILIZATION DATA (Five Star Meadows)")
    print("="*45)
    print(f"{'Category':<20} | {'Real-time (W)':<15} | {'Today (kWh)':<10}")
    print("-" * 45)
    print(f"{'PV (Self-consump.)':<20} | {metrics['PV Power']:>13.2f} | {metrics['Today PV']:>10.2f}")
    print(f"{'Battery Discharge':<20} | {metrics['Battery Discharge Power']:>13.2f} | {metrics['Today Discharge']:>10.2f}")
    print(f"{'Grid Import':<20} | {metrics['Grid Import Power']:>13.2f} | {metrics['Today Import']:>10.2f}")
    print("-" * 45)
    print(f"{'TOTAL CONSUMPTION':<20} | {metrics['Total Consumption Power']:>13.2f} | {metrics['Today Consumption']:>10.2f}")
    print("="*45)

    print(f"\nBreakdown Info:")
    print(f"- Total PV Generated:     {daily_pv_total:.2f} kWh")
    print(f"- PV Self-Consumption:    {metrics['Today PV']:.2f} kWh (Calculated)")
    print(f"- PV Exported to Grid:    {daily_export:.2f} kWh")
    
    # Explanation for 9.30
    if abs(metrics['Today PV'] - 9.30) > 1.0:
        print(f"\nNote: If you see 9.30 in the app, it matches the calculation:")
        print(f"      {daily_consumption:.2f} (Total) - {daily_discharge:.2f} (Batt) - {daily_import:.2f} (Grid) = {daily_consumption - daily_discharge - daily_import:.2f} kWh")

    
    # Debug: Print ALL keys only if something is missing
    if metrics['Today PV'] == 0 and daily_pv_total == 0:
        print("\nDEBUG: Full Data List...")
        for key, val in raw_values.items():
            print(f"  {key}: {val}")

    # Other useful metrics
    print(f"\nBattery SOC:              {raw_values.get('SOC', 0):>10.1f} %")
    print(f"Battery Status:           {'Charging' if metrics['Battery Charge Power'] > 0 else 'Discharging' if metrics['Battery Discharge Power'] > 0 else 'Idle'}")


if __name__ == "__main__":
    pull_utilization_data()
