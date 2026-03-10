from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.core.cache import cache
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
import io
from django.views import View
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db import models
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta, datetime
import pytz
import random
import string
import json
import logging

logger = logging.getLogger(__name__)
from django.contrib.auth.models import User
from .models import QuoteRequest, ContactMessage, JobApplication, NewsletterSubscriber, Customer, OTP, Payment, Wallet, Transaction, DeyeDevice, DeyeDeviceImage, PartnerInvoice, RFQ, RFQItem, Dispatch, PackingListItem, Incident, Alert, TeamMember, CustomerBilling, Notification, BillingUpdate, NotificationUpdate, IncidentUpdate, AlertUpdate, TeamMemberUpdate, CustomerUpdate, ApplicationUpdate, PartnerInvoiceUpdate, RFQUpdate, DispatchUpdate


@login_required
def payments_list(request):
    """View to list all customer payments"""
    customer = request.user.customer
    payments = Payment.objects.filter(customer=customer).order_by('-date')
    return render(request, 'payments.html', {'payments': payments})


@login_required
def payment_detail(request, payment_id):
    """View to show payment details"""
    customer = request.user.customer
    payment = Payment.objects.get(id=payment_id, customer=customer)
    return render(request, 'payment_detail.html', {'payment': payment})


from vegrid_app.services.deye_service import DeyeService, DeyeServiceError

@login_required
def device_data(request, device_sn):
    """AJAX endpoint to fetch real-time data for a device (station)"""
    try:
        # Check if user has permission to view this device
        customer = request.user.customer
        try:
            device = DeyeDevice.objects.get(device_sn=device_sn, customer=customer)
        except DeyeDevice.DoesNotExist:
            # Try one sync as fallback if device is missing for this customer
            service = DeyeService()
            service.sync_site_names(customer=customer)
            device = DeyeDevice.objects.get(device_sn=device_sn, customer=customer)
        
        # Using production-ready DeyeService
        service = DeyeService()
        data = service.get_station_detail(device_sn)
        
        # Extract station info from data if available
        station_info = {}
        if data and 'station_info_raw' in data:
            detail_data = data.get('station_info_raw', {})
            
            # Location logic (Prefer our DB values for County/Area/Town)
            location = device.location_address or f"{device.area}, {device.county}"
            if not device.location_address and (not device.area or not device.county):
                api_location = detail_data.get('address') or detail_data.get('location')
                if not api_location:
                    city = detail_data.get('city', '')
                    country = detail_data.get('countryName', '')
                    api_location = f"{city}, {country}" if city and country else (city or country or f"{device.town}, {device.country}")
                location = api_location
            
            # Weather info
            temp = detail_data.get('tmp')
            weather_name = detail_data.get('weatherName', '')
            weather_str = f"{temp}°C {weather_name}" if temp is not None else weather_name
            
            station_info = {
                'location': location,
                'latitude': str(device.latitude) if device.latitude else '',
                'longitude': str(device.longitude) if device.longitude else '',
                'weather': weather_str or 'Weather Unavailable',
                'timezone': detail_data.get('timezone', '3')
            }
            
            # Calculate site time (Prefer collectionTime from device if available)
            try:
                tz_val = station_info.get('timezone', '3')
                if not tz_val or tz_val == 'None':
                    tz_val = '3'
                
                # Base time source: either device collection time or current UTC
                device_ts = data.get('collectionTime')
                if device_ts:
                    try:
                        # Deye collectionTime is a Unix timestamp
                        base_time = datetime.fromtimestamp(int(device_ts), pytz.utc)
                    except (ValueError, TypeError):
                        base_time = datetime.now(pytz.utc)
                else:
                    base_time = datetime.now(pytz.utc)

                try:
                    # Try numeric offset first
                    offset = float(tz_val)
                    site_time = base_time + timedelta(hours=offset)
                except (ValueError, TypeError):
                    # Handle named timezone like 'Africa/Nairobi'
                    try:
                        tz = pytz.timezone(tz_val)
                        if device_ts:
                            try:
                                site_time = datetime.fromtimestamp(int(device_ts), tz)
                            except (ValueError, TypeError):
                                site_time = datetime.now(tz)
                        else:
                            site_time = datetime.now(tz)
                    except Exception:
                        # Final fallback to default offset
                        site_time = base_time + timedelta(hours=3)
                
                station_info['current_time'] = site_time.strftime('%H:%M:%S')
            except Exception as e:
                logger.warning(f"Error calculating site time in device_data: {e}")
                station_info['current_time'] = timezone.now().strftime('%H:%M:%S')

        if data:
            # Map standard fields
            formatted_data = {
                'pvPower': data.get('pvPower', 0),
                'gridPower': data.get('gridPower', 0),
                'batteryPower': data.get('batteryPower', 0),
                'loadPower': data.get('loadPower', 0),
                'batterySoc': data.get('batterySoc', 0),
                'totalPvPower': data.get('totalPvPower', 0),
                'dailyProduction': data.get('dailyProduction', 0),
                'dailyConsumption': data.get('dailyConsumption', 0),
                'dailyDischarge': data.get('dailyDischarge', 0),
                'dailyGridImport': data.get('dailyGridImport', 0),
                'pvSelfConsumption': data.get('pvSelfConsumption', 0),
                # Fallbacks for any missing today fields
                'generationToday': data.get('dailyProduction', 0),
                'batteryDischargeToday': data.get('dailyDischarge', 0),
                'consumptionToday': data.get('dailyConsumption', 0),
                'gridToday': data.get('dailyGridImport', 0),
                'is_fallback': data.get('is_fallback', False),
                'station_info': station_info
            }
            return JsonResponse({'status': 'success', 'data': formatted_data})
        else:
            return JsonResponse({'status': 'error', 'message': 'No data returned from DeyeCloud'}, status=504) # Gateway Timeout or similar

    except DeyeDevice.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Device not found'}, status=404)
    except DeyeServiceError as e:
        logger.warning(f"DeyeServiceError for {device_sn}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=e.status_code)
    except Exception as e:
        logger.error(f"Unexpected error in device_data: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'An internal server error occurred'}, status=500)


@login_required
def station_energy(request, station_id):
    """AJAX endpoint to fetch historical energy data for graphs"""
    try:
        # For security, verify this station belongs to the user
        customer = request.user.customer
        if not DeyeDevice.objects.filter(device_sn=station_id, customer=customer).exists():
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
            
        date = request.GET.get('date')
        service = DeyeService()
        data = service.get_station_energy_day(station_id, date)
        
        if data.get('code') in [0, "0", "1000000"]:
            return JsonResponse({'status': 'success', 'data': data.get('data')})
        else:
            status_code = data.get('status', 502)
            try:
                status_code = int(status_code)
                if not (400 <= status_code <= 599):
                    status_code = 502
            except (TypeError, ValueError):
                status_code = 502
            return JsonResponse({
                'status': 'error', 
                'message': data.get('msg', data.get('message', 'Failed to fetch energy data'))
            }, status=status_code)
            
    except Exception as e:
        logger.error(f"Error in station_energy: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def filtered_data(request, station_id):
    """AJAX endpoint to fetch filtered data based on time period"""
    try:
        # For security, verify this station belongs to the user
        customer = request.user.customer
        service = DeyeService()
        
        try:
            device = DeyeDevice.objects.get(device_sn=station_id, customer=customer)
        except DeyeDevice.DoesNotExist:
            # Try one sync as fallback if device is missing for this customer
            service.sync_site_names(customer=customer)
            device = DeyeDevice.objects.get(device_sn=station_id, customer=customer)
            
        period = request.GET.get('period', 'day')
        real_station_id = service.get_station_id_by_device_sn(station_id)
        logger.info(f"Resolved station_id for {station_id}: {real_station_id}")
        
        if not real_station_id:
            # Fallback to station_id if resolution fails (it might be already a station_id)
            real_station_id = station_id
            
        # Fetch data based on period
        if period == 'day':
            data = service.get_station_energy_day(real_station_id, timezone.now().strftime('%Y-%m-%d'), device_sn=station_id)
        elif period == 'month':
            data = service.get_station_energy_month(real_station_id, timezone.now().strftime('%Y-%m'), device_sn=station_id)
        elif period == 'year':
            data = service.get_station_energy_year(real_station_id, str(timezone.now().year), device_sn=station_id)
        elif period == 'lifetime':
            data = service.get_station_energy_lifetime(real_station_id, device_sn=station_id)
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid period'}, status=400)
        
                # Fetch station details (Location, Weather, Timezone)
        station_info = {}
        latest_station_data = {}
        try:
            # Fetch latest station statistics (for today's metrics)
            latest_resp = service.get_station_latest(real_station_id)
            if latest_resp.get('code') in [0, "0", "1000000"]:
                latest_station_data = latest_resp.get('data', {})

            detail_resp = service.get_station_detail_by_id(real_station_id)
            if detail_resp.get('code') in [0, "0", "1000000"]:
                detail_data = detail_resp.get('data', {})
                
                # Location logic (Prefer our DB values for County/Area/Town)
                location = device.location_address or f"{device.area}, {device.county}"
                if not device.location_address and (not device.area or not device.county):
                    # Fallback to API if DB is empty
                    api_location = detail_data.get('address') or detail_data.get('location')
                    if not api_location:
                        city = detail_data.get('city', '')
                        country = detail_data.get('countryName', '')
                        api_location = f"{city}, {country}" if city and country else (city or country or f"{device.town}, {device.country}")
                    location = api_location
                
                # Weather info
                temp = detail_data.get('tmp')
                weather_name = detail_data.get('weatherName', '')
                weather_str = f"{temp}°C {weather_name}" if temp is not None else weather_name
                
                station_info = {
                    'location': location,
                    'latitude': str(device.latitude) if device.latitude else '',
                    'longitude': str(device.longitude) if device.longitude else '',
                    'weather': weather_str or 'Weather Unavailable',
                    'timezone': detail_data.get('timezone', '3'), # Default to EAT (UTC+3) for Kenya
                    'address': detail_data.get('address', '')
                }
                
                # Calculate site time based on timezone offset (Prefer collectionTime from device if available)
                try:
                    # Deye timezone can be a string or number representing offset from UTC
                    tz_val = station_info.get('timezone', '3')
                    if not tz_val or tz_val == 'None':
                        tz_val = '3'
                    
                    # Base time source: either device collection time or current UTC
                    device_ts = latest_station_data.get('collectionTime')
                    if device_ts:
                        try:
                            # Deye collectionTime is a Unix timestamp
                            base_time = datetime.fromtimestamp(int(device_ts), pytz.utc)
                        except (ValueError, TypeError):
                            base_time = datetime.now(pytz.utc)
                    else:
                        base_time = datetime.now(pytz.utc)

                    try:
                        # Try numeric offset first
                        offset = float(tz_val)
                        site_time = base_time + timedelta(hours=offset)
                    except (ValueError, TypeError):
                        # Handle named timezone like 'Africa/Nairobi'
                        try:
                            tz = pytz.timezone(tz_val)
                            if device_ts:
                                try:
                                    site_time = datetime.fromtimestamp(int(device_ts), tz)
                                except (ValueError, TypeError):
                                    site_time = datetime.now(tz)
                            else:
                                site_time = datetime.now(tz)
                        except Exception:
                            # Final fallback to default offset
                            site_time = base_time + timedelta(hours=3)
                    
                    station_info['current_time'] = site_time.strftime('%H:%M:%S')
                except Exception as e:
                    logger.warning(f"Error calculating site time in filtered_data: {e}")
                    station_info['current_time'] = timezone.now().strftime('%H:%M:%S')
        except Exception as e:
            logger.error(f"Error fetching station details: {e}")

        if data.get('code') in [0, "0", "1000000"]:
            # Normalize the data structure for the frontend (ensure it has 'items' list)
            api_data = data.get('data')
            if isinstance(api_data, list):
                # If API returned a list directly, wrap it in 'items'
                normalized_data = {'items': api_data}
            elif isinstance(api_data, dict) and 'items' not in api_data:
                # If it's a dict but doesn't have 'items', it might be a direct dict with energy values
                # or a different structure. We should handle it if known.
                normalized_data = api_data
            else:
                normalized_data = api_data or {'items': []}

            return JsonResponse({
                'status': 'success', 
                'data': normalized_data,
                'station_info': station_info,
                'generationToday': latest_station_data.get('generationToday', 0),
                'generationTotal': latest_station_data.get('generationTotal', 0),
                'batteryDischargeToday': latest_station_data.get('batteryDischargeToday', 0),
                'consumptionToday': latest_station_data.get('consumptionToday', 0),
                'gridToday': latest_station_data.get('gridToday', 0),
                'solarProductionToday': latest_station_data.get('solarProductionToday', 0)
            })
        else:
            logger.error(f"Deye API error for {real_station_id}: {data}")
            # Use status code from API if available, otherwise default to 502
            status_code = data.get('status', 502)
            # Ensure status_code is an int and in valid range
            try:
                status_code = int(status_code)
                if not (400 <= status_code <= 599):
                    status_code = 502
            except (TypeError, ValueError):
                status_code = 502
                
            return JsonResponse({
                'status': 'error', 
                'message': data.get('msg', data.get('message', 'Failed to fetch energy data')), 
                'code': data.get('code')
            }, status=status_code)
            
    except Exception as e:
        logger.error(f"Error in filtered_data: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def dashboard(request):
    """Customer dashboard view"""
    customer = request.user.customer
    service = DeyeService()
    
    # Sync site names and location details BEFORE filtering devices
    try:
        name_sync_cache_key = f'site_detail_sync_{customer.id}'
        if not cache.get(name_sync_cache_key):
            service.sync_site_names(customer=customer)
            cache.set(name_sync_cache_key, True, 3600) # 1 hour
    except Exception as e:
        logger.error(f"Error syncing site names in dashboard: {e}")

    devices = DeyeDevice.objects.filter(customer=customer)
    
    # Sync alerts for known devices
    try:
        for device in devices:
            cache_key = f'alert_sync_{device.device_sn}'
            if not cache.get(cache_key):
                service.get_alerts(device.device_sn, save_to_db=True)
                cache.set(cache_key, True, 900) # 15 minutes
    except Exception as e:
        logger.error(f"Error syncing alerts in dashboard: {e}")

    # Get dynamic data for modals
    billings = CustomerBilling.objects.filter(customer=customer).order_by('-date')
    incidents = Incident.objects.filter(customer=customer).order_by('-date')
    alerts = Alert.objects.filter(customer=customer).order_by('-date')
    notifications = Notification.objects.filter(
        models.Q(customer=customer) | models.Q(recipient_type='all')
    ).order_by('-date')

    # Calculate some summary stats for the profile/dashboard
    unpaid_billings = billings.filter(status__in=['pending', 'overdue'])
    total_unpaid = unpaid_billings.aggregate(models.Sum('amount'))['amount__sum'] or 0
    
    # Initial weather for first device
    initial_weather = "Weather Unavailable"
    if devices.exists():
        try:
            service = DeyeService()
            first_device = devices[0]
            real_id = service.get_station_id_by_device_sn(first_device.device_sn) or first_device.device_sn
            resp = service.get_station_detail_by_id(real_id)
            if resp.get('code') in [0, "0", "1000000"]:
                d = resp.get('data', {})
                temp = d.get('tmp')
                w_name = d.get('weatherName', '')
                if temp is not None:
                    initial_weather = f"{temp}°C {w_name}"
                elif w_name:
                    initial_weather = w_name
        except:
            pass

    # Extract unique locations for filtering
    countries = set(devices.values_list('country', flat=True))
    counties = set(devices.values_list('county', flat=True))
    towns = set(devices.values_list('town', flat=True))
    areas = set(devices.values_list('area', flat=True))
    
    # Add customer's own info if not in devices
    if customer.country: countries.add(customer.country)
    if customer.county: counties.add(customer.county)
    if customer.town: towns.add(customer.town)
    if customer.area: areas.add(customer.area)
    
    # Clean up None or empty strings
    countries = sorted([c for c in countries if c])
    counties = sorted([c for c in counties if c])
    towns = sorted([t for t in towns if t])
    areas = sorted([a for a in areas if a])

    context = {
        'devices': devices,
        'has_devices': devices.exists(),
        'customer': customer,
        'billings': billings,
        'unpaid_billings': unpaid_billings,
        'total_unpaid': total_unpaid,
        'incidents': incidents,
        'alerts': alerts,
        'open_alerts_count': alerts.filter(status='Open').count(),
        'notifications': notifications,
        'unread_notifications_count': notifications.filter(status='unread').count(),
        'initial_weather': initial_weather,
        'countries': countries,
        'counties': counties,
        'towns': towns,
        'areas': areas
    }
    return render(request, 'dashboard.html', context)


@login_required
def device_tou(request, device_sn):
    """AJAX endpoint to fetch TOU settings for a device"""
    try:
        customer = request.user.customer
        device = DeyeDevice.objects.get(device_sn=device_sn, customer=customer)
        
        from vegrid_app.deye_api import DeyeAPI
        api = DeyeAPI()
        token = device.get_token()
        if not token:
            return JsonResponse({'status': 'error', 'message': 'Failed to get API token'}, status=500)
            
        result = api.get_tou_config(token, device_sn)
        if result.get('code') == 0:
            return JsonResponse({'status': 'success', 'data': result['data']})
        else:
            return JsonResponse({'status': 'error', 'message': result.get('msg', 'Failed to fetch TOU config')}, status=500)
    except DeyeDevice.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Device not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def create_incident(request):
    """View to handle new incident submission from customer"""
    if request.method == 'POST':
        customer = request.user.customer
        incident_site = request.POST.get('incident_site')
        incident_type = request.POST.get('incident_type')
        details = request.POST.get('details')
        
        import uuid
        reference = f"INC-{uuid.uuid4().hex[:8].upper()}"
        
        incident = Incident.objects.create(
            customer=customer,
            incident_type=incident_type,
            recipient_type='Admin',
            recipient='VEGRID',
            sender=customer.user.get_full_name() or customer.user.username,
            reference=reference,
            status='New'
        )
        
        # Log the site in the update if needed, or we could add a site field to Incident
        IncidentUpdate.objects.create(
            incident=incident,
            user=request.user,
            content=f"Site: {incident_site}\nDetails: {details}"
        )
        
        return JsonResponse({
            'success': True,
            'reference': reference,
            'customer_name': customer.user.get_full_name() or customer.user.username
        })
    return JsonResponse({'success': False, 'message': 'Only POST allowed'}, status=405)


@login_required
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    try:
        customer = request.user.customer
        notification = Notification.objects.get(
            id=notification_id, 
            customer=customer
        )
        notification.status = 'read'
        notification.save()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        # Check if it's an "all" notification
        notification = Notification.objects.get(id=notification_id, recipient_type='all')
        # For "all" notifications, we might need a way to track read status per user
        # but for now let's just return success
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
@login_required
def api_notifications(request):
    """API endpoint to fetch notifications for the authenticated user"""
    try:
        customer = request.user.customer
        notifications = Notification.objects.filter(
            models.Q(customer=customer) | models.Q(recipient_type='all')
        ).order_by('-date')
        
        notifications_data = []
        for notification in notifications:
            notifications_data.append({
                'id': notification.id,
                'date': notification.date.isoformat(),
                'sender': notification.sender,
                'notification_type': notification.notification_type or "General",
                'message': notification.message,
                'status': notification.status,
                'reference': notification.reference
            })
            
        return JsonResponse({
            'status': 'success',
            'notifications': notifications_data,
            'unread_count': notifications.filter(status='unread').count()
        })
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def get_admin_dashboard_stats(request):
    """Helper to get aggregate or filtered stats for admin dashboard"""
    country_filter = request.GET.get('country')
    county_filter = request.GET.get('county')
    town_filter = request.GET.get('town')
    area_filter = request.GET.get('area')
    site_filter = request.GET.get('site')

    selected_site = None
    if site_filter:
        try:
            selected_site = DeyeDevice.objects.get(id=site_filter)
            country_filter = selected_site.country
            county_filter = selected_site.county
            town_filter = selected_site.town
            area_filter = selected_site.area
        except DeyeDevice.DoesNotExist:
            pass

    sites = DeyeDevice.objects.all()

    if site_filter:
        sites = sites.filter(id=site_filter)
    else:
        if country_filter:
            sites = sites.filter(country=country_filter)
        if county_filter:
            sites = sites.filter(county=county_filter)
        if town_filter:
            sites = sites.filter(town=town_filter)
        if area_filter:
            sites = sites.filter(area=area_filter)

    total_generation = sites.aggregate(models.Sum('generation'))['generation__sum'] or 0
    grid_imports = sites.aggregate(models.Sum('grid_imports'))['grid_imports__sum'] or 0
    grid_export = sites.aggregate(models.Sum('grid_export'))['grid_export__sum'] or 0
    total_storage = sites.aggregate(models.Sum('storage'))['storage__sum'] or 0
    total_consumption = sites.aggregate(models.Sum('load'))['load__sum'] or 0
    
    net_grid = grid_imports - grid_export
    avg_soc = sites.exclude(battery_soc=None).aggregate(models.Avg('battery_soc'))['battery_soc__avg'] or 0
    
    total_revenue = Payment.objects.filter(status='Completed').aggregate(models.Sum('amount'))['amount__sum'] or 0
    total_wallet_balance = Wallet.objects.aggregate(models.Sum('current_balance'))['current_balance__sum'] or 0
    today_gen = sites.aggregate(models.Sum('today_generation'))['today_generation__sum'] or 0

    return {
        'total_sites': DeyeDevice.objects.count(),
        'online_sites': DeyeDevice.objects.filter(status='Online').count(),
        'total_customers': Customer.objects.count(),
        'total_payments': Payment.objects.count(),
        'total_revenue': total_revenue,
        'total_wallet_balance': total_wallet_balance,
        'open_incidents': Incident.objects.filter(status='Open').count(),
        'active_alerts': Alert.objects.exclude(status='Resolved').count(),
        'total_generation': f"{total_generation:.2f}",
        'today_generation': f"{today_gen:.2f}",
        'grid': f"{abs(net_grid):.2f}",
        'grid_direction': 'import' if net_grid >= 0 else 'export',
        'total_storage': f"{abs(total_storage):.2f}",
        'storage_direction': 'discharge' if total_storage >= 0 else 'charge',
        'avg_soc': int(avg_soc),
        'consumption': f"{total_consumption:.2f}",
        'selected_site_name': selected_site.name if selected_site else None,
        'selected_site_sn': selected_site.device_sn if selected_site else None,
        'selected_site_customer': selected_site.customer.user.get_full_name() or selected_site.customer.user.username if selected_site else None,
        'last_sync': selected_site.updated_at.strftime("%H:%M:%S") if selected_site else timezone.now().strftime("%H:%M:%S")
    }

@login_required
def admin_dashboard_data(request):
    """AJAX endpoint for admin dashboard real-time updates"""
    stats = get_admin_dashboard_stats(request)
    return JsonResponse({
        'status': 'success',
        'stats': stats
    })

@login_required
def admin_dashboard(request):
    """Admin dashboard view"""
    # Trigger real-time sync for all sites on page load
    service = DeyeService()
    service.sync_all_realtime_data()

    stats = get_admin_dashboard_stats(request)
    
    country_filter = request.GET.get('country')
    county_filter = request.GET.get('county')
    town_filter = request.GET.get('town')
    area_filter = request.GET.get('area')
    site_filter = request.GET.get('site')

    if site_filter:
        try:
            site_obj = DeyeDevice.objects.get(id=site_filter)
            country_filter = site_obj.country
            county_filter = site_obj.county
            town_filter = site_obj.town
            area_filter = site_obj.area
        except DeyeDevice.DoesNotExist:
            pass

    all_devices = DeyeDevice.objects.all()
    countries = all_devices.values_list('country', flat=True).distinct()
    
    counties_qs = all_devices
    if country_filter: counties_qs = counties_qs.filter(country=country_filter)
    counties = counties_qs.values_list('county', flat=True).distinct()
    
    towns_qs = counties_qs
    if county_filter: towns_qs = towns_qs.filter(county=county_filter)
    towns = towns_qs.values_list('town', flat=True).distinct()
    
    areas_qs = towns_qs
    if town_filter: areas_qs = areas_qs.filter(town=town_filter)
    areas = areas_qs.values_list('area', flat=True).distinct()

    return render(request, 'admin/dashboard.html', {
        'stats': stats,
        'selected_site': DeyeDevice.objects.filter(id=site_filter).first() if site_filter else None,
        'countries': sorted([c for c in countries if c]),
        'counties': sorted([c for c in counties if c]),
        'towns': sorted([t for t in towns if t]),
        'areas': sorted([a for a in areas if a]),
        'all_sites': all_devices.order_by('name'),
        'filters': {
            'country': country_filter,
            'county': county_filter,
            'town': town_filter,
            'area': area_filter,
            'site': site_filter,
        }
    })


@login_required
def admin_billings(request):
    """View to list all customer billings"""
    billings = CustomerBilling.objects.all().order_by('-date')
    
    total_billings = billings.aggregate(models.Sum('amount'))['amount__sum'] or 0
    total_paid = billings.filter(status='paid').aggregate(models.Sum('amount'))['amount__sum'] or 0
    total_balance = total_billings - total_paid
    
    stats = {
        'total_bills': billings.count(),
        'total_billings': total_billings,
        'total_paid': total_paid,
        'total_balance': total_balance,
    }
    
    return render(request, 'admin/billings.html', {
        'billings': billings,
        'stats': stats
    })


@login_required
def admin_billing_update(request, reference):
    """View to update a customer billing"""
    billing = CustomerBilling.objects.get(reference=reference)
    if request.method == 'POST':
        content = request.POST.get('notes')
        if content:
            BillingUpdate.objects.create(
                billing=billing,
                user=request.user,
                content=content
            )
            return redirect('admin-billings')
            
    updates = billing.updates.all().order_by('-date')
    return render(request, 'admin/billing_update.html', {
        'billing': billing,
        'reference': reference,
        'updates': updates
    })


@login_required
def admin_payments(request):
    """View to list all customer payments (admin version)"""
    payments = Payment.objects.all().order_by('-date')
    return render(request, 'admin/payments.html', {'payments': payments})


@login_required
def admin_payment_update(request, reference):
    """View to update a customer payment"""
    payment = Payment.objects.get(reference=reference)
    return render(request, 'admin/payment_update.html', {
        'payment': payment,
        'reference': reference
    })


@login_required
def admin_partner_invoices(request):
    """View to list all partner invoices"""
    invoices = PartnerInvoice.objects.all().order_by('-date')
    return render(request, 'admin/partner_invoices.html', {'invoices': invoices})


@login_required
def admin_partner_invoice_update(request, reference):
    """View to update a partner invoice"""
    invoice = PartnerInvoice.objects.get(reference=reference)
    if request.method == 'POST':
        content = request.POST.get('notes')
        if content:
            PartnerInvoiceUpdate.objects.create(
                invoice=invoice,
                user=request.user,
                content=content
            )
            return redirect('admin-partner-invoices')
            
    updates = invoice.updates.all().order_by('-date')
    return render(request, 'admin/partner_invoice_update.html', {
        'invoice': invoice,
        'reference': reference,
        'updates': updates
    })


@login_required
def admin_rfqs(request):
    """View to list all RFQs"""
    rfqs = RFQ.objects.all().order_by('-date')
    first_rfq = rfqs.first()
    items = first_rfq.items.all() if first_rfq else []
    return render(request, 'admin/rfqs.html', {'rfqs': rfqs, 'items': items, 'first_rfq': first_rfq})


@login_required
def admin_rfq_update(request, reference):
    """View to update an RFQ"""
    rfq = RFQ.objects.get(number=reference)
    if request.method == 'POST':
        content = request.POST.get('notes')
        if content:
            RFQUpdate.objects.create(
                rfq=rfq,
                user=request.user,
                content=content
            )
            return redirect('admin-rfqs')
            
    updates = rfq.updates.all().order_by('-date')
    return render(request, 'admin/rfq_update.html', {
        'rfq': rfq,
        'reference': reference,
        'updates': updates
    })


@login_required
def admin_dispatches(request):
    """View to list all dispatches"""
    dispatches = Dispatch.objects.all().order_by('-date')
    first_dispatch = dispatches.first()
    packing_list = first_dispatch.packing_list.all() if first_dispatch else []
    return render(request, 'admin/dispatches.html', {'dispatches': dispatches, 'packing_list': packing_list, 'first_dispatch': first_dispatch})


@login_required
def admin_dispatch_update(request, reference):
    """View to update a dispatch"""
    dispatch = Dispatch.objects.get(reference=reference)
    if request.method == 'POST':
        content = request.POST.get('notes')
        if content:
            DispatchUpdate.objects.create(
                dispatch=dispatch,
                user=request.user,
                content=content
            )
            return redirect('admin-dispatches')
            
    updates = dispatch.updates.all().order_by('-date')
    return render(request, 'admin/dispatch_update.html', {
        'dispatch': dispatch,
        'reference': reference,
        'updates': updates
    })


@login_required
def admin_wallet(request):
    """View to show admin wallet"""
    transactions = Transaction.objects.all().order_by('-transaction_date', '-transaction_time')
    
    total_credits = transactions.filter(credit_debit='credit').aggregate(models.Sum('amount'))['amount__sum'] or 0
    total_debits = transactions.filter(credit_debit='debit').aggregate(models.Sum('amount'))['amount__sum'] or 0
    wallet_balance = total_credits - total_debits
    
    stats = {
        'wallet_balance': wallet_balance,
        'total_credits': transactions.filter(credit_debit='credit').count(),
        'total_debits': transactions.filter(credit_debit='debit').count(),
    }
    
    return render(request, 'admin/wallet.html', {
        'transactions': transactions,
        'stats': stats
    })


def team_create_login(request, user_id, otp_code, role):
    """View to allow a new team member to create their password"""
    user = get_object_or_404(User, id=user_id)
    
    # Check if OTP exists and is valid
    otp = OTP.objects.filter(
        user=user, 
        otp_code=otp_code, 
        otp_type='registration', 
        is_used=False,
        expires_at__gte=timezone.now()
    ).first()
    
    if not otp:
        return HttpResponse("Invalid or expired registration link.")
        
    if request.method == 'POST':
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        if password and password == confirm_password:
            # Update password
            user.set_password(password)
            user.save()
            
            # Mark registration link OTP as used
            otp.is_used = True
            otp.save()
            
            # Generate new OTP for verification
            new_otp = generate_otp(length=6)
            expires_at = timezone.now() + timedelta(minutes=15)
            OTP.objects.create(
                user=user,
                otp_code=new_otp,
                expires_at=expires_at,
                otp_type='email' 
            )
            
            # Send verification OTP to email and phone
            send_email_otp(user.email, new_otp)
            send_sms(user.team_member.contact, f"Your VEGRID team registration OTP is: {new_otp}")
            
            return redirect('team-verify-otp', user_id=user.id)
        else:
            return render(request, 'team_create_login.html', {'user': user, 'error': "Passwords do not match."})
            
    return render(request, 'team_create_login.html', {'user': user})


def team_verify_otp(request, user_id):
    """View to verify OTP after password creation"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        otp_code = request.POST.get('otp_code')
        
        otp = OTP.objects.filter(
            user=user,
            otp_code=otp_code,
            is_used=False,
            expires_at__gte=timezone.now()
        ).first()
        
        if otp:
            otp.is_used = True
            otp.save()
            
            # Activate user
            user.is_active = True
            user.save()
            
            # Log user in
            login(request, user)
            
            # Redirect based on role
            role = user.team_member.role
            if role == 'Admin' or role == 'Supervisor':
                return redirect('admin-dashboard')
            else:
                return redirect('dashboard')
        else:
            return render(request, 'team_verify_otp.html', {'user': user, 'error': "Invalid or expired OTP."})
            
    return render(request, 'team_verify_otp.html', {'user': user})


@login_required
def admin_team(request):
    """View to list all team members"""
    team = TeamMember.objects.all()
    
    stats = {
        'total_members': team.count(),
        'total_active': team.filter(status='Active').count(),
        'total_inactive': team.filter(status='Inactive').count(),
        'total_suspended': team.filter(status='Suspended').count(),
    }
    
    return render(request, 'admin/team.html', {
        'team': team,
        'stats': stats
    })


@login_required
def admin_team_update(request, email):
    """View to update a team member"""
    member = TeamMember.objects.get(email=email)
    if request.method == 'POST':
        content = request.POST.get('notes')
        if content:
            TeamMemberUpdate.objects.create(
                member=member,
                user=request.user,
                content=content
            )
            return redirect('admin-team')
            
    updates = member.updates.all().order_by('-date')
    return render(request, 'admin/team_update.html', {
        'member': member,
        'email': email,
        'updates': updates
    })


@login_required
def admin_team_new(request):
    """View to add a new team member"""
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        middle_name = request.POST.get('middle_name')
        last_name = request.POST.get('last_name')
        id_number = request.POST.get('id_number')
        pin_number = request.POST.get('pin_number')
        contact = request.POST.get('contact')
        email = request.POST.get('email')
        address = request.POST.get('address')
        town = request.POST.get('town')
        country = request.POST.get('country')
        role = request.POST.get('role')
        registration_type = request.POST.get('registration_type')
        registration_number = request.POST.get('registration_number')
        qualification = request.POST.get('qualification')
        documents = request.FILES.get('documents')
        photo = request.FILES.get('photo')

        if first_name and last_name and email:
            # Generate unique username
            base_username = f"{first_name.lower()}.{last_name.lower()}"
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            # Create inactive user
            temp_password = User.objects.make_random_password()
            new_user = User.objects.create_user(
                username=username,
                email=email,
                password=temp_password,
                first_name=first_name,
                last_name=last_name,
                is_active=False # User must complete registration
            )
            
            # Add to group if needed (e.g. staff)
            new_user.is_staff = True
            new_user.save()

            member = TeamMember.objects.create(
                user=new_user,
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name,
                id_number=id_number,
                pin_number=pin_number,
                contact=contact,
                email=email,
                address=address,
                town=town,
                country=country,
                role=role,
                registration_type=registration_type,
                registration_number=registration_number,
                qualification=qualification,
                documents=documents,
                photo=photo
            )
            
            # Generate OTP for link verification
            otp_code = generate_otp(length=6)
            expires_at = timezone.now() + timedelta(days=1)
            OTP.objects.create(
                user=new_user,
                otp_code=otp_code,
                expires_at=expires_at,
                otp_type='registration'
            )
            
            # Send instructions via email and SMS
            import urllib.parse
            safe_role = urllib.parse.quote(role)
            login_link = f"http://{request.get_host()}/team/create-login/{new_user.id}/{otp_code}/{safe_role}/"
            sms_msg = f"Welcome to VEGRID! Your username is: {username}. Create password: {login_link}"
            
            send_team_registration_email(email, first_name, username, login_link)
            send_sms(contact, sms_msg)

            return redirect('admin-team')
    return render(request, 'admin/team_new.html')


@login_required
def admin_team_edit(request, email):
    """View to edit a team member's details"""
    member = TeamMember.objects.get(email=email)
    if request.method == 'POST':
        member.first_name = request.POST.get('first_name')
        member.middle_name = request.POST.get('middle_name')
        member.last_name = request.POST.get('last_name')
        member.id_number = request.POST.get('id_number')
        member.pin_number = request.POST.get('pin_number')
        member.contact = request.POST.get('contact')
        member.email = request.POST.get('email')
        member.address = request.POST.get('address')
        member.town = request.POST.get('town')
        member.country = request.POST.get('country')
        member.role = request.POST.get('role')
        member.registration_type = request.POST.get('registration_type')
        member.registration_number = request.POST.get('registration_number')
        member.qualification = request.POST.get('qualification')
        member.status = request.POST.get('status', member.status)
        
        if request.FILES.get('documents'):
            member.documents = request.FILES.get('documents')
        if request.FILES.get('photo'):
            member.photo = request.FILES.get('photo')
            
        member.save()
        
        # Update user object as well
        if member.user:
            member.user.first_name = member.first_name
            member.user.last_name = member.last_name
            member.user.email = member.email
            member.user.save()
            
        return redirect('admin-team')
        
    return render(request, 'admin/team_edit.html', {'member': member})


@login_required
def admin_team_print(request):
    """View to print the team list"""
    email = request.GET.get('email')
    if email:
        team = TeamMember.objects.filter(email=email)
    else:
        team = TeamMember.objects.all()
    
    all_team = TeamMember.objects.all()
    stats = {
        'total_members': all_team.count(),
        'total_active': all_team.filter(status='Active').count(),
        'total_inactive': all_team.filter(status='Inactive').count(),
        'total_suspended': all_team.filter(status='Suspended').count(),
    }
    return render(request, 'admin/team_print.html', {'team': team, 'stats': stats})


@login_required
def admin_notifications(request):
    """View to list all notifications"""
    notifications = Notification.objects.all().order_by('-date')
    return render(request, 'admin/notifications.html', {'notifications': notifications})


@login_required
def admin_notification_update(request, id):
    """View to update a notification"""
    notification = Notification.objects.get(id=id)
    if request.method == 'POST':
        content = request.POST.get('notes')
        if content:
            NotificationUpdate.objects.create(
                notification=notification,
                user=request.user,
                content=content
            )
            return redirect('admin-notifications')
            
    updates = notification.updates.all().order_by('-date')
    return render(request, 'admin/notification_update.html', {
        'notification': notification,
        'id': id,
        'updates': updates
    })


@login_required
def admin_notification_new(request):
    """View to create a new notification"""
    if request.method == 'POST':
        notification_type = request.POST.get('notification_type')
        recipient_type = request.POST.get('recipient_type')
        customer_id = request.POST.get('customer_id')
        message = request.POST.get('message')
        
        customer = None
        recipient_name = "All Customers"
        
        if customer_id:
            customer = Customer.objects.get(id=customer_id)
            recipient_name = customer.user.get_full_name() or customer.user.username
            
        import uuid
        reference = f"NOT-{uuid.uuid4().hex[:8].upper()}"
        
        Notification.objects.create(
            notification_type=notification_type,
            recipient_type=recipient_type,
            customer=customer,
            recipient_name=recipient_name,
            message=message,
            reference=reference,
            status='unread'
        )
        return redirect('admin-notifications')
        
    customers = Customer.objects.all()
    return render(request, 'admin/notification_new.html', {'customers': customers})


@login_required
def admin_incidents(request):
    """View to list all incidents"""
    incidents = Incident.objects.all().order_by('-date')
    return render(request, 'admin/incidents.html', {'incidents': incidents})


@login_required
def admin_incident_update(request, id):
    """View to update an incident"""
    incident = Incident.objects.get(id=id)
    if request.method == 'POST':
        content = request.POST.get('notes')
        if content:
            IncidentUpdate.objects.create(
                incident=incident,
                user=request.user,
                content=content
            )
            return redirect('admin-incidents')
            
    updates = incident.updates.all().order_by('-date')
    return render(request, 'admin/incident_update.html', {
        'incident': incident,
        'id': id,
        'updates': updates
    })


@login_required
def admin_incident_new(request):
    """View to create a new incident"""
    if request.method == 'POST':
        incident_type = request.POST.get('incident_type')
        recipient_type = request.POST.get('recipient_type')
        customer_id = request.POST.get('customer_id')
        message = request.POST.get('message')
        
        customer = None
        recipient = "Unknown"
        
        if customer_id:
            customer = Customer.objects.get(id=customer_id)
            recipient = customer.user.get_full_name() or customer.user.username
            
        import uuid
        reference = f"INC-{uuid.uuid4().hex[:8].upper()}"
        
        incident = Incident.objects.create(
            incident_type=incident_type,
            recipient_type=recipient_type,
            recipient=recipient,
            customer=customer,
            sender=request.user.get_full_name() or request.user.username,
            reference=reference,
            status='New'
        )
        
        # Create initial update
        IncidentUpdate.objects.create(
            incident=incident,
            user=request.user,
            content=message
        )
        
        return redirect('admin-incidents')
        
    customers = Customer.objects.all()
    return render(request, 'admin/incident_new.html', {'customers': customers})


@login_required
def admin_alerts(request):
    """View to list all alerts"""
    alerts = Alert.objects.all().order_by('-date')
    
    stats = {
        'total_alerts': alerts.count(),
        'total_resolved': alerts.filter(status='Resolved').count(),
        'total_closed': alerts.filter(status='Closed').count(),
        'total_open': alerts.filter(status='Open').count(),
    }
    
    return render(request, 'admin/alerts.html', {
        'alerts': alerts,
        'stats': stats
    })


@login_required
def admin_alert_update(request, id):
    """View to update an alert"""
    alert = Alert.objects.get(id=id)
    if request.method == 'POST':
        content = request.POST.get('notes')
        if content:
            AlertUpdate.objects.create(
                alert=alert,
                user=request.user,
                content=content
            )
            return redirect('admin-alerts')
            
    updates = alert.updates.all().order_by('-date')
    return render(request, 'admin/alert_update.html', {
        'alert': alert,
        'id': id,
        'updates': updates
    })


@login_required
def api_alerts(request):
    """API endpoint to fetch alerts for the authenticated user"""
    try:
        customer = request.user.customer
        logger.info(f"Fetching alerts for customer: {customer.id}")
        
        # Get customer's devices
        devices = DeyeDevice.objects.filter(customer=customer)
        
        alerts_data = []
        
        # For each device, get alerts from Deye Cloud
        for device in devices:
            logger.info(f"Checking device: {device.device_sn}")
            try:
                service = DeyeService()
                device_alerts = service.get_alerts(device.device_sn)
                
                # Add device alerts to main list
                alerts_data.extend(device_alerts)
                
            except Exception as e:
                logger.error(f"Error getting alerts for device {device.device_sn}: {str(e)}")
                continue
        
        # If no alerts from Deye Cloud, check database
        if not alerts_data:
            logger.info("No alerts from Deye Cloud, checking database")
            alerts = Alert.objects.filter(customer=customer).order_by('-date')
            
            for alert in alerts:
                alert_data = {
                    'id': alert.id,
                    'date': alert.date.isoformat(),
                    'site': alert.site,
                    'source': alert.source,
                    'alert_type': alert.alert_type,
                    'severity': alert.severity,
                    'status': alert.status,
                    'message': alert.message,
                    'updates': [
                        {
                            'id': update.id,
                            'date': update.date.isoformat(),
                            'user': update.user.username,
                            'content': update.content
                        } for update in alert.updates.all().order_by('-date')
                    ]
                }
                alerts_data.append(alert_data)
        
        # Sort alerts by date (descending)
        alerts_data.sort(key=lambda x: x['date'], reverse=True)
        
        logger.info(f"Returning {len(alerts_data)} alerts")
        return JsonResponse({'alerts': alerts_data})
        
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_admin_alerts(request):
    """API endpoint to fetch all alerts for admin users"""
    try:
        # Check if user is admin (you might need to adjust this check based on your permissions system)
        if not request.user.is_staff:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
            
        alerts = Alert.objects.all().order_by('-date')
        
        # Serialize alerts to JSON
        alerts_data = []
        for alert in alerts:
            alert_data = {
                'id': alert.id,
                'date': alert.date.isoformat(),
                'customer': alert.customer.user.email,
                'site': alert.site,
                'source': alert.source,
                'alert_type': alert.alert_type,
                'severity': alert.severity,
                'status': alert.status,
                'updates': [
                    {
                        'id': update.id,
                        'date': update.date.isoformat(),
                        'user': update.user.username,
                        'content': update.content
                    } for update in alert.updates.all().order_by('-date')
                ]
            }
            alerts_data.append(alert_data)
        
        return JsonResponse({'alerts': alerts_data})
    except Exception as e:
        logger.error(f"Error fetching admin alerts: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def admin_applications(request):
    """View to list all quote requests/applications"""
    applications = QuoteRequest.objects.all().order_by('-created_at')
    
    stats = {
        'total_apps': applications.count(),
        'total_commissioned': applications.filter(status='Commissioned').count(),
        'total_commenced': applications.filter(status='Commenced').count(),
        'total_stopped': applications.filter(status='Stopped').count(),
        'total_confirmed': applications.filter(status='Confirmed').count(),
        'total_closed': applications.filter(status='Closed').count(),
    }
    
    return render(request, 'admin/applications.html', {
        'applications': applications,
        'stats': stats
    })


@login_required
def admin_application_update(request, reference):
    """View to update an application"""
    application = QuoteRequest.objects.get(reference=reference)
    if request.method == 'POST':
        content = request.POST.get('notes')
        status = request.POST.get('status')
        if content:
            ApplicationUpdate.objects.create(
                quote_request=application,
                user=request.user,
                content=content
            )
        if status:
            application.status = status
            application.save()
            
        return redirect('admin-applications')
            
    updates = application.updates.all().order_by('-date')
    return render(request, 'admin/application_update.html', {
        'application': application,
        'reference': reference,
        'updates': updates
    })


@login_required
def admin_customers(request):
    """View to list all customers"""
    # Sync data for all active sites to ensure consumption is up to date
    for device in DeyeDevice.objects.all():
        device.sync_consumption_data()
        
    customers = Customer.objects.all()
    
    total_sites = DeyeDevice.objects.count()
    total_rating = DeyeDevice.objects.aggregate(models.Sum('rating'))['rating__sum'] or 0
    total_consumption = DeyeDevice.objects.aggregate(models.Sum('total_consumption'))['total_consumption__sum'] or 0
    today_consumption = DeyeDevice.objects.aggregate(models.Sum('today_consumption'))['today_consumption__sum'] or 0
    total_generation = DeyeDevice.objects.aggregate(models.Sum('total_generation'))['total_generation__sum'] or 0
    today_generation = DeyeDevice.objects.aggregate(models.Sum('today_generation'))['today_generation__sum'] or 0
    
    stats = {
        'total_customers': customers.count(),
        'total_sites': total_sites,
        'total_active': customers.filter(is_verified=True).count(),
        'total_inactive': customers.filter(is_verified=False).count(),
        'total_rating': f"{total_rating:.2f}",
        'total_consumption': f"{total_consumption:.2f}",
        'today_consumption': f"{today_consumption:.2f}",
        'total_generation': f"{total_generation:.2f}",
        'today_generation': f"{today_generation:.2f}",
    }
    
    return render(request, 'admin/customers.html', {
        'customers': customers,
        'stats': stats
    })


@login_required
def admin_customer_download_pdf(request, customer_id):
    """View to download a single customer's details as PDF"""
    customer = Customer.objects.get(id=customer_id)
    
    # Create a file-like buffer to receive PDF data.
    buffer = io.BytesIO()

    # Create the PDF object, using the buffer as its "file."
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Draw header
    p.setFont("Helvetica-Bold", 16)
    p.drawString(2 * cm, height - 2 * cm, "VEGRID CUSTOMER REPORT")
    
    p.setFont("Helvetica", 10)
    p.drawString(2 * cm, height - 2.6 * cm, f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
    p.line(2 * cm, height - 2.8 * cm, width - 2 * cm, height - 2.8 * cm)

    # Customer Details
    y = height - 4 * cm
    p.setFont("Helvetica-Bold", 12)
    p.drawString(2 * cm, y, f"Customer: {customer.customer_id}")
    
    y -= 1 * cm
    p.setFont("Helvetica-Bold", 10)
    p.drawString(2 * cm, y, "PERSONAL INFORMATION")
    p.line(2 * cm, y - 0.2 * cm, 8 * cm, y - 0.2 * cm)
    
    y -= 0.8 * cm
    p.setFont("Helvetica", 10)
    details = [
        ("Name", customer.get_full_name() or customer.user.username),
        ("Email", customer.user.email),
        ("Phone", customer.phone_number),
        ("ID/Passport", customer.id_number or "N/A"),
        ("PIN", customer.pin_number or "N/A"),
        ("Reg Type", customer.registration_type.title()),
    ]
    
    for label, value in details:
        p.drawString(2 * cm, y, f"{label}:")
        p.drawString(6 * cm, y, str(value))
        y -= 0.5 * cm

    # Site Summary
    y -= 0.5 * cm
    p.setFont("Helvetica-Bold", 10)
    p.drawString(2 * cm, y, "SITE SUMMARY")
    p.line(2 * cm, y - 0.2 * cm, 8 * cm, y - 0.2 * cm)
    
    y -= 0.8 * cm
    p.setFont("Helvetica", 10)
    summary = [
        ("Total Sites", str(customer.deye_devices.count())),
        ("Aggregate Rating (kVA)", f"{customer.aggregate_rating:.2f}"),
        ("Aggregate Storage (kW)", f"{customer.aggregate_storage:.2f}"),
        ("Today Generation (kWh)", f"{customer.aggregate_generation_today:.2f}"),
        ("Total Generation (kWh)", f"{customer.aggregate_generation_total:.2f}"),
        ("Today Consumption (kWh)", f"{customer.aggregate_consumption_today:.2f}"),
        ("Total Consumption (kWh)", f"{customer.aggregate_consumption_total:.2f}"),
    ]
    
    for label, value in summary:
        p.drawString(2 * cm, y, f"{label}:")
        p.drawString(8 * cm, y, str(value))
        y -= 0.5 * cm

    # Sites Table
    y -= 1 * cm
    p.setFont("Helvetica-Bold", 10)
    p.drawString(2 * cm, y, "CONNECTED SITES")
    p.line(2 * cm, y - 0.2 * cm, 8 * cm, y - 0.2 * cm)
    
    y -= 1 * cm
    # Table headers
    p.setFont("Helvetica-Bold", 9)
    p.drawString(2 * cm, y, "Site Name")
    p.drawString(6 * cm, y, "Serial Number")
    p.drawString(10 * cm, y, "Town")
    p.drawString(14 * cm, y, "Status")
    p.line(2 * cm, y - 0.2 * cm, width - 2 * cm, y - 0.2 * cm)
    
    y -= 0.6 * cm
    p.setFont("Helvetica", 9)
    for site in customer.deye_devices.all():
        if y < 2 * cm: # Page break logic
            p.showPage()
            y = height - 2 * cm
            p.setFont("Helvetica", 9)
            
        p.drawString(2 * cm, y, site.name[:20])
        p.drawString(6 * cm, y, site.device_sn)
        p.drawString(10 * cm, y, site.town or "N/A")
        p.drawString(14 * cm, y, site.status)
        y -= 0.5 * cm

    # Close the PDF object cleanly, and we're done.
    p.showPage()
    p.save()

    # FileResponse sets the Content-Disposition header so that browsers
    # present the option to save the file.
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="customer_{customer.customer_id}.pdf"'
    
    return response


@login_required
def admin_customer_print(request, customer_id):
    """View to print a single customer's details"""
    customer = Customer.objects.get(id=customer_id)
    return render(request, 'admin/customer_print.html', {
        'customer': customer,
    })


@login_required
def admin_customers_print_all(request):
    """View to print all customers"""
    customers = Customer.objects.all()
    return render(request, 'admin/customers_print_all.html', {
        'customers': customers,
    })


@login_required
def admin_customer_update(request, customer_id):
    """View to update a customer"""
    customer = Customer.objects.get(id=customer_id)
    
    # Sync consumption data for this customer's devices
    for device in customer.deye_devices.all():
        device.sync_consumption_data()
        
    if request.method == 'POST':
        content = request.POST.get('notes')
        if content:
            CustomerUpdate.objects.create(
                customer=customer,
                user=request.user,
                content=content
            )
            return redirect('admin-customers')
            
    updates = customer.updates.all().order_by('-date')
    return render(request, 'admin/customer_update.html', {
        'customer': customer,
        'customer_id': customer_id,
        'updates': updates
    })


@login_required
def admin_site_new(request):
    """View to create a new site (DeyeDevice)"""
    if request.method == 'POST':
        customer_id = request.POST.get('customer_id')
        name = request.POST.get('name')
        device_sn = request.POST.get('device_sn')
        deye_username = request.POST.get('deye_username')
        deye_password = request.POST.get('deye_password')
        county = request.POST.get('county')
        town = request.POST.get('town')
        area = request.POST.get('area')
        rating = request.POST.get('rating') or 0
        storage = request.POST.get('storage') or 0
        
        if customer_id and name and device_sn:
            # Check if serial number already exists to ensure site is linked only once
            if DeyeDevice.objects.filter(device_sn=device_sn).exists():
                customers = Customer.objects.all()
                return render(request, 'admin/site_new.html', {
                    'customers': customers,
                    'error': f"A site with Serial Number '{device_sn}' is already linked to a customer."
                })
                
            customer = Customer.objects.get(id=customer_id)
            DeyeDevice.objects.create(
                customer=customer,
                name=name,
                device_sn=device_sn,
                deye_username=deye_username,
                deye_password=deye_password,
                county=county,
                town=town,
                area=area,
                rating=rating,
                storage=storage
            )
            return redirect('admin-sites')
            
    customers = Customer.objects.all()
    return render(request, 'admin/site_new.html', {'customers': customers})


@login_required
def admin_sites(request):
    """View to list all sites"""
    from django.db.models import Sum
    sites = DeyeDevice.objects.all()
    
    # Calculate stats
    total_rating = sites.aggregate(Sum('rating'))['rating__sum'] or 0
    total_generation = sites.aggregate(Sum('installed_capacity'))['installed_capacity__sum'] or 0
    total_storage = sites.aggregate(Sum('storage'))['storage__sum'] or 0
    total_grid_imports = sites.aggregate(Sum('grid_imports'))['grid_imports__sum'] or 0
    total_grid_export = sites.aggregate(Sum('grid_export'))['grid_export__sum'] or 0
    
    return render(request, 'admin/sites.html', {
        'sites': sites,
        'total_rating': total_rating,
        'total_generation': total_generation,
        'total_storage': total_storage,
        'total_grid_imports': total_grid_imports,
        'total_grid_export': total_grid_export
    })


@login_required
def admin_system_setup(request):
    """View to list all sites for system setup"""
    sites = DeyeDevice.objects.all().order_by('-created_at')
    return render(request, 'admin/system_setup.html', {'sites': sites})


@login_required
def admin_system_setup_new(request):
    """View to create a new site using the System Setup form"""
    if request.method == 'POST':
        # General Information
        name = request.POST.get('name')
        country = request.POST.get('country')
        county = request.POST.get('county')
        town = request.POST.get('town')
        area = request.POST.get('area')
        service_area = request.POST.get('service_area')
        location_address = request.POST.get('location_address')
        coordinates = request.POST.get('coordinates')
        time_zone = request.POST.get('time_zone')
        
        # System Information
        rating = request.POST.get('rating') or 0
        inverter_brand = request.POST.get('inverter_brand')
        inverter_model = request.POST.get('inverter_model')
        device_sn = request.POST.get('device_sn')
        installed_capacity = request.POST.get('installed_capacity') or 0
        battery_capacity = request.POST.get('battery_capacity') or 0
        battery_brand = request.POST.get('battery_brand')
        
        # Installation Information
        customer_id = request.POST.get('customer_id')
        installer = request.POST.get('installer')
        installation_engineer = request.POST.get('installation_engineer')
        installation_date = request.POST.get('installation_date')
        
        # Commission Information
        owner = request.POST.get('owner')
        financier_type = request.POST.get('financier_type', 'Customer')
        financier = request.POST.get('financier_name')
        currency = request.POST.get('currency', 'KES')
        deye_username = request.POST.get('deye_username')
        deye_password = request.POST.get('deye_password')
        service_rep = request.POST.get('service_rep')

        # Handle latitude/longitude from coordinates (expecting "lat, lon")
        latitude = None
        longitude = None
        if coordinates and ',' in coordinates:
            try:
                lat, lon = coordinates.split(',')
                latitude = float(lat.strip())
                longitude = float(lon.strip())
            except ValueError:
                pass

        if name and device_sn and customer_id:
            # Check if serial number already exists
            if DeyeDevice.objects.filter(device_sn=device_sn).exists():
                return render(request, 'admin/system_setup_new.html', {
                    'error': f"A site with Serial Number '{device_sn}' already exists.",
                    'customers': Customer.objects.all(),
                    'team_members': TeamMember.objects.all()
                })
                
            try:
                customer = Customer.objects.get(id=customer_id)
                site = DeyeDevice.objects.create(
                    customer=customer,
                    name=name,
                    device_sn=device_sn,
                    deye_username=deye_username,
                    deye_password=deye_password,
                    country=country,
                    county=county,
                    town=town,
                    area=area,
                    service_area=service_area,
                    location_address=location_address,
                    latitude=latitude,
                    longitude=longitude,
                    time_zone=time_zone,
                    rating=rating,
                    inverter_brand=inverter_brand,
                    inverter_model=inverter_model,
                    installed_capacity=installed_capacity,
                    battery_capacity=battery_capacity,
                    battery_brand=battery_brand,
                    installer=installer,
                    installation_engineer=installation_engineer,
                    installation_date=installation_date if installation_date and installation_date != "" else None,
                    owner=owner,
                    financier_type=financier_type,
                    financier=financier,
                    currency=currency,
                    service_rep=service_rep
                )
                
                # Handle images (up to 6)
                for i in range(1, 7):
                    img = request.FILES.get(f'image_{i}')
                    if img:
                        DeyeDeviceImage.objects.create(device=site, image=img)
                
                # Set status as Pending for preview
                site.status = 'Pending'
                site.save()
                        
                return redirect('admin-system-setup-preview', site_id=site.id)
            except Exception as e:
                # Handle error
                return render(request, 'admin/system_setup_new.html', {
                    'error': str(e),
                    'customers': Customer.objects.all(),
                    'team_members': TeamMember.objects.all()
                })
            
    customers = Customer.objects.all()
    team_members = TeamMember.objects.all()
    return render(request, 'admin/system_setup_new.html', {
        'customers': customers,
        'team_members': team_members
    })


@login_required
def admin_system_setup_edit(request, site_id):
    """View to edit an existing site configuration"""
    site = DeyeDevice.objects.get(id=site_id)
    if request.method == 'POST':
        # General Information
        site.name = request.POST.get('name')
        site.country = request.POST.get('country')
        site.county = request.POST.get('county')
        site.town = request.POST.get('town')
        site.area = request.POST.get('area')
        site.service_area = request.POST.get('service_area')
        site.location_address = request.POST.get('location_address')
        coordinates = request.POST.get('coordinates')
        site.time_zone = request.POST.get('time_zone')
        
        # System Information
        new_device_sn = request.POST.get('device_sn')
        
        # Check if serial number already exists for another device
        if DeyeDevice.objects.filter(device_sn=new_device_sn).exclude(id=site_id).exists():
             return render(request, 'admin/system_setup_edit.html', {
                'error': f"A site with Serial Number '{new_device_sn}' already exists.",
                'site': site,
                'customers': Customer.objects.all(),
                'team_members': TeamMember.objects.all()
            })
            
        site.device_sn = new_device_sn
        site.rating = request.POST.get('rating') or 0
        site.inverter_brand = request.POST.get('inverter_brand')
        site.inverter_model = request.POST.get('inverter_model')
        site.installed_capacity = request.POST.get('installed_capacity') or 0
        site.battery_capacity = request.POST.get('battery_capacity') or 0
        site.battery_brand = request.POST.get('battery_brand')
        
        # Installation Information
        customer_id = request.POST.get('customer_id')
        site.installer = request.POST.get('installer')
        site.installation_engineer = request.POST.get('installation_engineer')
        installation_date = request.POST.get('installation_date')
        site.installation_date = installation_date if installation_date and installation_date != "" else None
        
        # Commission Information
        site.owner = request.POST.get('owner')
        site.financier_type = request.POST.get('financier_type', 'Owner')
        site.financier = request.POST.get('financier_name')
        site.currency = request.POST.get('currency', 'KES')
        site.deye_username = request.POST.get('deye_username')
        site.deye_password = request.POST.get('deye_password')
        site.service_rep = request.POST.get('service_rep')

        # Handle latitude/longitude from coordinates
        if coordinates and ',' in coordinates:
            try:
                lat, lon = coordinates.split(',')
                site.latitude = float(lat.strip())
                site.longitude = float(lon.strip())
            except ValueError:
                pass

        try:
            if customer_id:
                site.customer = Customer.objects.get(id=customer_id)
            site.save()
            
            # Handle new images
            for i in range(1, 7):
                img = request.FILES.get(f'image_{i}')
                if img:
                    DeyeDeviceImage.objects.create(device=site, image=img)
            
            # Set status to Pending for preview
            site.status = 'Pending'
            site.save()
                    
            return redirect('admin-system-setup-preview', site_id=site.id)
        except Exception as e:
            return render(request, 'admin/system_setup_edit.html', {
                'error': str(e),
                'site': site,
                'customers': Customer.objects.all(),
                'team_members': TeamMember.objects.all()
            })
            
    customers = Customer.objects.all()
    team_members = TeamMember.objects.all()
    # Format coordinates for display
    coords_display = ""
    if site.latitude and site.longitude:
        coords_display = f"{site.latitude}, {site.longitude}"
        
    return render(request, 'admin/system_setup_edit.html', {
        'site': site,
        'customers': customers,
        'team_members': team_members,
        'coords_display': coords_display
    })


@login_required
def admin_system_setup_preview(request, site_id):
    """View to preview the site configuration before final confirmation"""
    site = DeyeDevice.objects.get(id=site_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'confirm':
            site.status = 'Online'
            site.save()
            return redirect('admin-sites')
        elif action == 'back':
            # If site is already Online, go back to sites list, otherwise go back to edit
            if site.status == 'Online':
                return redirect('admin-sites')
            return redirect('admin-system-setup-edit', site_id=site.id)
            
    # Format coordinates for display
    coords_display = ""
    if site.latitude and site.longitude:
        coords_display = f"{site.latitude}, {site.longitude}"
        
    return render(request, 'admin/system_setup_preview.html', {
        'site': site,
        'coords_display': coords_display
    })


@login_required
def admin_system_setup_delete(request, site_id):
    """View to delete a site configuration"""
    site = get_object_or_404(DeyeDevice, id=site_id)
    if request.method == 'POST':
        site.delete()
        return redirect('admin-sites')
    return render(request, 'admin/site_confirm_delete.html', {'site': site})


@login_required
def admin_system_setup_images(request, site_id):
    """View to show all images for a site"""
    site = get_object_or_404(DeyeDevice, id=site_id)
    return render(request, 'admin/system_setup_images.html', {'site': site})


def index(request):
    """Homepage view"""
    return render(request, 'index.html')


def about(request):
    """About page view"""
    return render(request, 'about.html')


def solutions(request):
    """Solutions page view"""
    return render(request, 'solutions.html')


def how_it_works(request):
    """How it works page view"""
    return render(request, 'how-it-works.html')


def impact(request):
    """Impact page view"""
    return render(request, 'impact.html')


def careers(request):
    """Careers page view"""
    return render(request, 'careers.html')


def team(request):
    """Team page view"""
    return render(request, 'team.html')


def get_quote(request):
    """Get quote page view"""
    if request.method == 'POST':
        # Handle form submission
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        business_name = request.POST.get('business-name')
        industry = request.POST.get('industry')
        energy_consumption = request.POST.get('energy-consumption')
        location = request.POST.get('location')
        roof_type = request.POST.get('roof-type')
        additional_info = request.POST.get('additional-info')
        
        # Save data to database
        QuoteRequest.objects.create(
            name=name,
            email=email,
            phone=phone,
            business_name=business_name,
            industry=industry,
            energy_consumption=energy_consumption,
            location=location,
            roof_type=roof_type,
            additional_info=additional_info
        )
        
        # Return success response
        return HttpResponse('Quote request received! We will contact you within 24 hours.')
    
    return render(request, 'get-quote.html')


def partners(request):
    """Partners page view"""
    return render(request, 'partners.html')


def investors(request):
    """Investors page view"""
    return render(request, 'investors.html')


def contact(request):
    """Contact page view"""
    if request.method == 'POST':
        # Handle form submission
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        # Save data to database
        ContactMessage.objects.create(
            name=name,
            email=email,
            phone=phone,
            subject=subject,
            message=message
        )
        
        # Return success response
        return HttpResponse('Thank you for your message! We will get back to you within 24 hours.')
    
    return render(request, 'contact.html')


def careers_apply(request):
    """Careers application form handler"""
    if request.method == 'POST':
        # Handle form submission
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        position = request.POST.get('position')
        experience = request.POST.get('experience')
        cover_letter = request.POST.get('coverLetter')
        resume = request.FILES.get('resume')
        
        # Save data to database
        JobApplication.objects.create(
            name=name,
            email=email,
            phone=phone,
            position=position,
            experience=experience,
            cover_letter=cover_letter,
            resume=resume
        )
        
        # Return success response
        return HttpResponse('Thank you for your application! We will review it and get back to you soon.')
    
    return HttpResponse('Method not allowed', status=405)


def generate_otp(length=4):
    """Generate a numeric OTP of specified length"""
    return ''.join(random.choices(string.digits, k=length))


from django.core.mail import send_mail
from django.conf import settings
import os
import requests

def send_sms(phone_number, message):
    """Generic function to send SMS using Africa's Talking"""
    username = os.getenv('AFRICAS_TALKING_USERNAME')
    api_key = os.getenv('AFRICAS_TALKING_API_KEY')
    
    if username and api_key:
        try:
            import africastalking
            africastalking.initialize(username, api_key)
            sms = africastalking.SMS
            # Clean phone number
            clean_phone = phone_number.strip().replace(' ', '')
            if not clean_phone.startswith('+'):
                clean_phone = '+' + clean_phone
            sms.send(message, [clean_phone])
            return True
        except Exception as e:
            print(f"SMS sending failed: {e}")
            
            # Fallback to requests if SDK not installed or failed
            try:
                import requests
                url = "https://api.africastalking.com/version1/messaging"
                headers = {"ApiKey": api_key, "Content-Type": "application/x-www-form-urlencoded"}
                clean_phone = phone_number.strip().replace(' ', '')
                if not clean_phone.startswith('+'):
                    clean_phone = '+' + clean_phone
                data = {"username": username, "to": clean_phone, "message": message}
                response = requests.post(url, headers=headers, data=data)
                if response.status_code == 201:
                    return True
            except Exception as e2:
                print(f"SMS fallback failed: {e2}")
    
    # Debug print
    print(f"DEBUG SMS: To {phone_number}: {message}")
    return False


def send_team_registration_email(email, first_name, username, login_link):
    """Send registration instructions to new team member"""
    subject = "Welcome to VEGRID - Complete Your Registration"
    message = f"""
    Hi {first_name},

    Welcome to VEGRID! Your team account has been created.

    Your username is: {username}

    Please click the link below to create your password and complete your registration:
    {login_link}

    This link will expire in 24 hours.

    Best regards,
    The VEGRID Team
    """
    try:
        from django.core.mail import send_mail
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
        return True
    except Exception as e:
        print(f"Failed to send registration email: {e}")
        return False


def send_sms_otp(phone_number, otp_code):
    """Send OTP via SMS using Africa's Talking only"""
    # Print OTP to terminal for debugging
    print(f"\n=== SMS OTP DEBUG ===")
    print(f"Original Phone: {phone_number}")
    
    # Clean phone number - ensure it's in correct format
    clean_phone = phone_number.strip().replace(' ', '')
    
    # Remove any leading zeros after the plus sign
    if clean_phone.startswith('+'):
        # Split into country code and number
        country_code = clean_phone[:4]  # +254
        number_part = clean_phone[4:]
        
        # Remove leading zeros from number part
        number_part = number_part.lstrip('0')
        
        # Reconstruct with proper format
        clean_phone = country_code + number_part
    
    # Ensure it has plus prefix
    if not clean_phone.startswith('+'):
        # If it's just numbers, assume it needs +254
        if clean_phone.isdigit():
            if clean_phone.startswith('254'):
                clean_phone = '+' + clean_phone
            elif clean_phone.startswith('0'):
                clean_phone = '+254' + clean_phone[1:]
            else:
                clean_phone = '+254' + clean_phone
        else:
            clean_phone = '+' + clean_phone
    
    print(f"Cleaned Phone: {clean_phone}")
    print(f"OTP Code: {otp_code}")
    print(f"======================\n")
    
    # Africa's Talking
    username = os.getenv('AFRICAS_TALKING_USERNAME')
    api_key = os.getenv('AFRICAS_TALKING_API_KEY')
    
    if username and api_key:
        try:
            import africastalking
            africastalking.initialize(username, api_key)
            sms = africastalking.SMS
            response = sms.send(f"Your VEGRID OTP is: {otp_code}", [clean_phone])
            print(f"Africa's Talking response: {response}")
            return True
        except ImportError:
            # Fallback to requests if SDK not installed
            url = "https://api.africastalking.com/version1/messaging"
            headers = {"ApiKey": api_key, "Content-Type": "application/x-www-form-urlencoded"}
            data = {"username": username, "to": clean_phone, "message": f"Your VEGRID OTP is: {otp_code}"}
            response = requests.post(url, headers=headers, data=data)
            print(f"Africa's Talking HTTP response: {response.status_code}, {response.text}")
            if response.status_code == 201:
                return True
        except Exception as e:
            print(f"Africa's Talking failed: {e}")
    
    # Fallback for development/testing - print OTP to console
    print(f"WARNING: SMS sending failed. OTP for {clean_phone} is: {otp_code}")
    
    # In development mode, we can consider the OTP as "sent" for testing purposes
    from django.conf import settings
    if settings.DEBUG:
        print("Development mode: OTP sent successfully (printed to console)")
        return True
    
    return False
def send_email_otp(email, otp_code):
    """Send OTP via email using Django's email system"""
    subject = "Your VEGRID Verification Code"
    message = f"""
    Hi,

    Your verification code is: {otp_code}

    This code will expire in 5 minutes. Please do not share this code with anyone.

    Thank you,
    The VEGRID Team
    """
    
    # Print OTP to terminal for debugging
    print(f"=== EMAIL OTP DEBUG ===")
    print(f"Email: {email}")
    print(f"OTP Code: {otp_code}")
    print(f"Expires: 5 minutes from now")
    print(f"========================")
    
    try:
        from django.core.mail import send_mail
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
        print(f"Email OTP {otp_code} sent successfully to {email}")
        return True
    except Exception as e:
        print(f"Failed to send email OTP to {email}: {e}")
        return False


def send_terms_conditions_email(email, username):
    """Send terms and conditions email to new user"""
    subject = "Welcome to VEGRID - Terms and Conditions"
    message = f"""
    Hi {username},

    Welcome to VEGRID! We're excited to have you as a customer.

    Please find attached our Terms and Conditions for your reference.

    Thank you for choosing VEGRID!

    Best regards,
    The VEGRID Team
    """
    
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
        return True
    except Exception as e:
        print(f"Failed to send terms and conditions email: {e}")
        return False


@method_decorator(csrf_exempt, name='dispatch')
class SendPhoneOtpView(View):
    """API endpoint to send phone verification OTP"""
    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid request data'}, status=400)
        
        phone_number = data.get('phone_number')
        country = data.get('country')
        registration_type = data.get('registration_type')
        
        # Clean and format the phone number
        if phone_number:
            # Remove any spaces, dashes, or parentheses
            phone_number = ''.join(filter(str.isdigit, phone_number))
            
            # If it starts with '0' (Kenyan format), replace with '254'
            if phone_number.startswith('0'):
                phone_number = '254' + phone_number[1:]
            # If it doesn't start with country code, add it based on selected country
            elif not phone_number.startswith('254') and not phone_number.startswith('+'):
                # Get country code from the selected country
                country_codes = {
                    'kenya': '254',
                    'uganda': '256',
                    'tanzania': '255',
                    'rwanda': '250',
                    'burundi': '257',
                    'DRC Congo': '243'
                }
                country_code = country_codes.get(country, '254')
                phone_number = country_code + phone_number
            
            # Ensure it has the plus prefix for international format
            if not phone_number.startswith('+'):
                phone_number = '+' + phone_number
        
        # Check if user exists with this phone number (store without + for consistency)
        stored_phone = phone_number.replace('+', '')
        existing_customer = Customer.objects.filter(
            Q(phone_number=stored_phone) | Q(phone_number=phone_number)
        ).first()
        
        if existing_customer:
            return JsonResponse({'success': False, 'message': 'Phone number already registered'}, status=400)
        
        # Create or get user (using the cleaned phone number for username)
        username = stored_phone  # Use cleaned number without +
        email = f"{stored_phone}@temp.com"
        
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'password': User.objects.make_random_password()
            }
        )
        
        # Create customer profile with formatted phone number
        customer, customer_created = Customer.objects.get_or_create(
            user=user,
            defaults={
                'phone_number': phone_number,  # Store with + for display
                'registration_type': registration_type.lower(),
            }
        )
        
        # Generate OTP
        otp_code = generate_otp()
        expires_at = timezone.now() + timedelta(minutes=5)
        
        # Create OTP record
        OTP.objects.create(
            user=user,
            otp_code=otp_code,
            expires_at=expires_at,
            otp_type='phone'
        )
        
        # Send OTP via SMS (use the properly formatted number)
        print(f"Attempting to send OTP {otp_code} to {phone_number}")
        sms_sent = send_sms_otp(phone_number, otp_code)
        
        if sms_sent:
            print(f"Successfully sent OTP {otp_code} to {phone_number}")
        else:
            print(f"Failed to send OTP {otp_code} to {phone_number}")
        
        return JsonResponse({
            'success': True,
            'message': 'OTP sent successfully',
            'otp_length': 4,
            'expires_in': 300,
            'formatted_number': phone_number  # Return formatted number for debugging
        })

@method_decorator(csrf_exempt, name='dispatch')
class VerifyPhoneOtpView(View):
    """API endpoint to verify phone OTP"""
    def post(self, request):
        data = json.loads(request.body)
        phone_number = data.get('phone_number')
        otp_code = data.get('otp_code')
        
        customer = Customer.objects.filter(phone_number=phone_number).first()
        
        if not customer:
            return JsonResponse({'success': False, 'message': 'User not found'}, status=404)
        
        user = customer.user
        
        # Find valid OTP
        otp = OTP.objects.filter(
            user=user,
            otp_code=otp_code,
            otp_type='phone',
            is_used=False,
            expires_at__gte=timezone.now()
        ).first()
        
        if not otp:
            return JsonResponse({'success': False, 'message': 'Invalid or expired OTP'}, status=400)
        
        # Mark OTP as used
        otp.is_used = True
        otp.save()
        
        # Mark customer as verified (phone verified)
        customer.is_verified = True
        customer.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Phone number verified successfully',
            'user_id': user.id
        })


@method_decorator(csrf_exempt, name='dispatch')
class CompleteRegistrationView(View):
    """API endpoint to complete user registration with personal details"""
    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid request data'}, status=400)
        phone_number = data.get('phone_number')
        first_name = data.get('first_name')
        middle_name = data.get('middle_name')
        last_name = data.get('last_name')
        email = data.get('email')
        id_number = data.get('id_number')
        pin_number = data.get('pin_number')
        address = data.get('address')
        county = data.get('county')
        town = data.get('town')
        passport_photo = data.get('passport_photo')  # Base64 or file
        
        customer = Customer.objects.filter(phone_number=phone_number).first()
        
        if not customer:
            return JsonResponse({'success': False, 'message': 'User not found'}, status=404)
        
        user = customer.user
        
        # Check if email is already taken by another user
        if User.objects.filter(Q(username=email) | Q(email=email)).exclude(pk=user.pk).exists():
            return JsonResponse({'success': False, 'message': 'This email address is already registered'}, status=400)
            
        # Update user details
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.username = email
        
        # Update customer details
        customer.id_number = id_number
        customer.pin_number = pin_number
        customer.address = address
        customer.county = county
        customer.town = town
        
        if passport_photo:
            # Handle passport photo upload
            pass
        
        user.save()
        customer.save()
        
        # Send email verification OTP
        otp_code = generate_otp()
        expires_at = timezone.now() + timedelta(minutes=5)
        
        OTP.objects.create(
            user=user,
            otp_code=otp_code,
            expires_at=expires_at,
            otp_type='email'
        )
        
        send_email_otp(email, otp_code)
        
        return JsonResponse({
            'success': True,
            'message': 'Registration details saved. Verify your email.',
            'email': email
        })


@method_decorator(csrf_exempt, name='dispatch')
class ResendEmailOtpView(View):
    """API endpoint to resend email verification OTP"""
    def post(self, request):
        data = json.loads(request.body)
        email = data.get('email')
        
        user = User.objects.filter(email=email).first()
        
        if not user:
            return JsonResponse({'success': False, 'message': 'User not found'}, status=404)
        
        # Generate new OTP
        otp_code = generate_otp()
        expires_at = timezone.now() + timedelta(minutes=5)
        
        # Create OTP record
        OTP.objects.create(
            user=user,
            otp_code=otp_code,
            expires_at=expires_at,
            otp_type='email'
        )
        
        # Send OTP via email
        print(f"Attempting to send email OTP {otp_code} to {email}")
        email_sent = send_email_otp(email, otp_code)
        
        if email_sent:
            print(f"Successfully sent email OTP {otp_code} to {email}")
            return JsonResponse({
                'success': True,
                'message': 'Email OTP resent successfully',
                'otp_length': 4,
                'expires_in': 300
            })
        else:
            print(f"Failed to send email OTP {otp_code} to {email}")
            return JsonResponse({'success': False, 'message': 'Failed to send email OTP'}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class VerifyEmailOtpView(View):
    """API endpoint to verify email OTP"""
    def post(self, request):
        data = json.loads(request.body)
        email = data.get('email')
        otp_code = data.get('otp_code')
        
        user = User.objects.filter(email=email).first()
        
        if not user:
            return JsonResponse({'success': False, 'message': 'User not found'}, status=404)
        
        # Find valid OTP
        otp = OTP.objects.filter(
            user=user,
            otp_code=otp_code,
            otp_type='email',
            is_used=False,
            expires_at__gte=timezone.now()
        ).first()
        
        if not otp:
            return JsonResponse({'success': False, 'message': 'Invalid or expired OTP'}, status=400)
        
        # Mark OTP as used
        otp.is_used = True
        otp.save()
        
        # Send terms and conditions email
        send_terms_conditions_email(email, user.get_full_name())
        
        return JsonResponse({
            'success': True,
            'message': 'Email verified successfully. Welcome to VEGRID!',
            'user_id': user.id
        })


@method_decorator(csrf_exempt, name='dispatch')
class CompleteOtherDetailsView(View):
    """API endpoint to save the final registration details"""
    def post(self, request):
        data = json.loads(request.body)
        phone_number = data.get('phone_number')
        id_number = data.get('id_number')
        pin_number = data.get('pin_number')
        address = data.get('address')
        county = data.get('county')
        town = data.get('town')
        
        customer = Customer.objects.filter(phone_number=phone_number).first()
        
        if not customer:
            return JsonResponse({'success': False, 'message': 'User not found'}, status=404)
        
        # Update customer details
        customer.id_number = id_number
        customer.pin_number = pin_number
        customer.address = address
        customer.county = county
        customer.town = town
        customer.save()
        
        # Log the user in automatically after registration is complete
        login(request, customer.user)
        
        return JsonResponse({
            'success': True,
            'message': 'Final details saved successfully',
            'redirect_url': '/dashboard/'
        })


@method_decorator(csrf_exempt, name='dispatch')
class SendLoginOtpView(View):
    """API endpoint to send login OTP"""
    def post(self, request):
        data = json.loads(request.body)
        phone_number_or_username = data.get('phone_number')
        
        # Try finding by phone number first
        customer = Customer.objects.filter(phone_number=phone_number_or_username).first()
        
        # If not found, try finding by username
        if not customer:
            user = User.objects.filter(username=phone_number_or_username).first()
            if user:
                customer = getattr(user, 'customer', None)
        
        if not customer:
            return JsonResponse({'success': False, 'message': 'Account not found'}, status=404)
        
        phone_number = customer.phone_number
        if not phone_number:
            return JsonResponse({'success': False, 'message': 'No phone number associated with this account'}, status=400)
        
        # Generate 4-digit OTP
        otp_code = generate_otp(length=4)
        expires_at = timezone.now() + timedelta(minutes=5)
        
        OTP.objects.create(
            user=customer.user,
            otp_code=otp_code,
            expires_at=expires_at,
            otp_type='phone'
        )
        
        send_sms_otp(phone_number, otp_code)
        
        return JsonResponse({
            'success': True,
            'message': 'Login OTP sent successfully'
        })


@method_decorator(csrf_exempt, name='dispatch')
class VerifyLoginOtpView(View):
    """API endpoint to verify login OTP and log user in"""
    def post(self, request):
        data = json.loads(request.body)
        phone_number_or_username = data.get('phone_number')
        otp_code = data.get('otp_code')
        
        # Try finding by phone number first
        customer = Customer.objects.filter(phone_number=phone_number_or_username).first()
        
        # If not found, try finding by username
        if not customer:
            user = User.objects.filter(username=phone_number_or_username).first()
            if user:
                customer = getattr(user, 'customer', None)
        
        if not customer:
            return JsonResponse({'success': False, 'message': 'User not found'}, status=404)
        
        otp = OTP.objects.filter(
            user=customer.user,
            otp_code=otp_code,
            otp_type='phone',
            is_used=False,
            expires_at__gte=timezone.now()
        ).first()
        
        if not otp:
            return JsonResponse({'success': False, 'message': 'Invalid or expired OTP'}, status=400)
        
        otp.is_used = True
        otp.save()
        
        # Log the user in
        login(request, customer.user)
        
        # Determine redirect URL based on user type
        redirect_url = '/dashboard/'
        if customer.user.is_staff or customer.user.is_superuser:
            redirect_url = '/admin-dashboard/'
        
        return JsonResponse({
            'success': True,
            'message': 'Login successful',
            'redirect_url': redirect_url
        })


@login_required
def wallet_dashboard(request):
    """View to show wallet dashboard"""
    customer = request.user.customer
    wallet, created = Wallet.objects.get_or_create(customer=customer)
    
    transactions = Transaction.objects.filter(wallet=wallet).order_by('-transaction_date', '-transaction_time')
    return render(request, 'wallet/dashboard.html', {
        'wallet': wallet,
        'transactions': transactions
    })


@login_required
def wallet_transaction_detail(request, transaction_id):
    """View to show single transaction details"""
    customer = request.user.customer
    transaction = Transaction.objects.get(id=transaction_id, wallet__customer=customer)
    return render(request, 'wallet/transaction_detail.html', {'transaction': transaction})


@login_required
def wallet_top_up(request):
    """View to handle wallet top up"""
    customer = request.user.customer
    wallet, created = Wallet.objects.get_or_create(customer=customer)
    
    if request.method == 'POST':
        # In a real app, we'd integrate with Mpesa/Bank here
        amount_str = request.POST.get('amount', '0').replace(',', '') or '0'
        amount = float(amount_str)
        source = request.POST.get('source')
        number = request.POST.get('number')
        
        # Simulating a transaction
        reference = f"TOP{random.randint(10000, 99999)}"
        transaction = Transaction.objects.create(
            wallet=wallet,
            amount=amount,
            credit_debit='credit',
            transaction_type='Top Up',
            originator='customer',
            reference=reference,
            status='completed',
            source_destination=source,
            source_destination_number=number
        )
        
        # Update balance
        wallet.current_balance += amount
        wallet.available_balance += amount
        wallet.save()
        
        return redirect('wallet-confirmation', transaction_id=transaction.id)
        
    return render(request, 'wallet/top_up.html', {'wallet': wallet})


@login_required
def wallet_transfer(request):
    """View to handle wallet transfer"""
    customer = request.user.customer
    wallet, created = Wallet.objects.get_or_create(customer=customer)
    
    if request.method == 'POST':
        amount_str = request.POST.get('amount', '0').replace(',', '') or '0'
        amount = float(amount_str)
        destination = request.POST.get('destination')
        number = request.POST.get('number')
        
        if wallet.available_balance >= amount:
            # Simulating a transaction
            reference = f"TRF{random.randint(10000, 99999)}"
            transaction = Transaction.objects.create(
                wallet=wallet,
                amount=amount,
                credit_debit='debit',
                transaction_type='Transfer',
                originator='customer',
                reference=reference,
                status='completed',
                source_destination=destination,
                source_destination_number=number
            )
            
            # Update balance
            wallet.current_balance -= amount
            wallet.available_balance -= amount
            wallet.save()
            
            return redirect('wallet-confirmation', transaction_id=transaction.id)
        else:
            # Simulation failure
            return render(request, 'wallet/failure.html', {
                'error': 'Insufficient balance',
                'customer': customer
            })
            
    return render(request, 'wallet/transfer.html', {'wallet': wallet})


@login_required
def wallet_confirmation(request, transaction_id):
    """View to show transaction confirmation"""
    customer = request.user.customer
    transaction = Transaction.objects.get(id=transaction_id, wallet__customer=customer)
    return render(request, 'wallet/confirmation.html', {
        'transaction': transaction,
        'customer': customer
    })


def logout_view(request):
    """Logout view"""
    logout(request)
    return redirect('index')


def newsletter_subscribe(request):
    """Newsletter subscription handler"""
    if request.method == 'POST':
        email = request.POST.get('email')
        
        # Save data to database
        NewsletterSubscriber.objects.get_or_create(email=email)
        
        # Return success response
        return HttpResponse('Thank you for subscribing! You will receive our latest news and updates.')
    
    return HttpResponse('Method not allowed', status=405)


@login_required
def update_profile(request):
    """View to update customer profile via AJAX"""
    if request.method == 'POST':
        try:
            customer = request.user.customer
            user = request.user
            
            # Update User fields
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.email = request.POST.get('email', user.email)
            user.save()
            
            # Update Customer fields
            customer.middle_name = request.POST.get('middle_name', customer.middle_name)
            customer.phone_number = request.POST.get('phone_number', customer.phone_number)
            customer.id_number = request.POST.get('id_number', customer.id_number)
            customer.pin_number = request.POST.get('pin_number', customer.pin_number)
            customer.address = request.POST.get('address', customer.address)
            customer.county = request.POST.get('county', customer.county)
            customer.country = request.POST.get('country', customer.country)
            customer.area = request.POST.get('area', customer.area)
            customer.town = request.POST.get('town', customer.town)
            customer.save()

            # Sync to DeyeDevices (all sections)
            DeyeDevice.objects.filter(customer=customer).update(
                county=customer.county,
                area=customer.area,
                town=customer.town,
                country=customer.country
            )
            
            return JsonResponse({'success': True, 'message': 'Profile updated successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
            
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
