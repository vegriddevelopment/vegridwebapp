import os
import sys
import django
import requests
from datetime import datetime

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.services.deye_service import DeyeService

def verify_month_data():
    service = DeyeService()
    target_sn = "2510171733"
    print(f"--- Deye Monthly Metrics Verification for SN: {target_sn} ---")
    
    try:
        # Resolve to station ID
        station_id = service.get_station_id_by_device_sn(target_sn)
        if not station_id:
            stations_resp = service.get_station_list_with_device()
            stations = stations_resp.get('stationList', stations_resp.get('data', {}).get('list', []))
            for s in stations:
                for d in s.get('deviceListItems', []):
                    if str(d.get('deviceSn')) == target_sn:
                        station_id = s.get('id')
                        break
        
        if not station_id:
            print("FAILED: Could not find station ID for device.")
            return
            
        print(f"Resolved Station ID: {station_id}")

        months_to_test = ["2026-02", "2026-03"]
        token = service.get_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        url_hist = f"{service.base_url}/v1.0/device/history"
        for target_month in months_to_test:
            print(f"\n{'='*50}")
            print(f"FETCHING MONTH: {target_month} (Day-by-Day)")
            print(f"{'='*50}")

            month_gen = 0
            month_cons = 0
            days_found = 0

            # Iterate through days (1 to 28 or 31)
            num_days = 31 if target_month.endswith("03") else 28
            for day_num in range(1, num_days + 1):
                date_str = f"{target_month}-{day_num:02d}"
                
                payload_hist = {
                    "deviceSn": target_sn,
                    "measurePoints": ["DailyActiveProduction", "DailyConsumption", "DailyEnergyPurchased", "DailyDischargingEnergy"],
                    "startAt": date_str,
                    "endAt": date_str,
                    "granularity": 1
                }
                
                try:
                    resp_hist = requests.post(url_hist, params={"appId": service.app_id}, json=payload_hist, headers=headers, timeout=10)
                    hist_data = resp_hist.json()
                    
                    if hist_data.get('code') in [0, "0", "1000000"]:
                        d_list = hist_data.get('dataList', [])
                        if d_list:
                            # Get last point of the day
                            last_point = sorted(d_list, key=lambda x: int(x['time']))[-1]
                            vals = {i['key']: float(i['value']) for i in last_point.get('itemList', [])}
                            
                            gen = vals.get('DailyActiveProduction', 0)
                            cons = vals.get('DailyConsumption', 0)
                            grd = vals.get('DailyEnergyPurchased', 0)
                            dis = vals.get('DailyDischargingEnergy', 0)
                            
                            month_gen += gen
                            month_cons += cons
                            days_found += 1
                            print(f"  {date_str} | Gen: {gen:6.2f} | Cons: {cons:6.2f} | Grid: {grd:6.2f} | Dis: {dis:6.2f}")
                except Exception as e:
                    print(f"  {date_str} | ERROR: {str(e)}")

            print(f"\nMONTH TOTAL ({target_month}):")
            print(f"  Generation:  {month_gen:.2f} kWh")
            print(f"  Consumption: {month_cons:.2f} kWh")
            print(f"  Days with data: {days_found}")

        # 4. Try station/energy/year
        print(f"\nStep 4: Testing Native Station API (/v1.0/station/energy/year) for 2026...")
        url_year = f"{service.base_url}/v1.0/station/energy/year"
        payload_year = {"id": station_id, "year": "2026"}
        
        resp_year = requests.post(url_year, params={"appId": service.app_id}, json=payload_year, headers=headers)
        year_data = resp_year.json()
        
        if year_data.get('code') in [0, "0", "1000000"]:
            items = year_data.get('data', {}).get('items', [])
            print(f"Station Year API SUCCESS: {len(items)} months.")
            for i in items:
                print(f"Month: {i.get('month') or i.get('time')} -> Gen: {i.get('generation') or i.get('energy')}, Cons: {i.get('consumption')}")
        else:
            print(f"Station Year API FAILED: {year_data.get('status')} {year_data.get('error')}")

    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    verify_month_data()
