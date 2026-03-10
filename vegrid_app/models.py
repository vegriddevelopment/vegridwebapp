from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta
import hashlib
import json


class Customer(models.Model):
    """Customer model to store additional customer information"""
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE)
    customer_id = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name="Customer ID")
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    id_number = models.CharField(max_length=20, blank=True, null=True)
    pin_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=200, blank=True, null=True)
    county = models.CharField(max_length=100, blank=True, null=True)
    town = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    area = models.CharField(max_length=100, blank=True, null=True)
    passport_photo = models.ImageField(upload_to='passport_photos/', blank=True, null=True)
    registration_type = models.CharField(max_length=50, choices=[
        ('individual', 'Individual'),
        ('commercial', 'Commercial'),
        ('other', 'Other'),
    ], default='individual')
    is_verified = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        if not self.customer_id:
            # Get country prefix (default to 'KE' if not provided)
            country_prefix = self.country[:2].upper() if self.country else 'KE'
            
            # Get current date components
            from datetime import datetime
            now = datetime.now()
            day = str(now.day).zfill(2)
            month = str(now.month).zfill(2)
            year = str(now.year)[2:]  # 2-digit year (e.g., 2026 becomes 26)
            
            # Get next sequence number (prefix+day+month+year)
            last_customer = Customer.objects.filter(
                customer_id__startswith=f"{country_prefix}{day}{month}{year}"
            ).order_by('-customer_id').first()
            
            if last_customer:
                # Extract sequence number from last customer ID (last 4 digits)
                last_seq = int(last_customer.customer_id[-4:])
                next_seq = last_seq + 1
            else:
                next_seq = 1
                
            # Format sequence with 4 digits
            seq_number = str(next_seq).zfill(4)
            
            # Combine all parts (prefix, day, month, year, sequence)
            self.customer_id = f"{country_prefix}{day}{month}{year}{seq_number}"
            
        super().save(*args, **kwargs)

    @property
    def aggregate_rating(self):
        return self.deye_devices.aggregate(models.Sum('rating'))['rating__sum'] or 0.00

    @property
    def aggregate_storage(self):
        return self.deye_devices.aggregate(models.Sum('storage'))['storage__sum'] or 0.00

    @property
    def aggregate_consumption_total(self):
        return self.deye_devices.aggregate(models.Sum('total_consumption'))['total_consumption__sum'] or 0.00

    @property
    def aggregate_consumption_today(self):
        return self.deye_devices.aggregate(models.Sum('today_consumption'))['today_consumption__sum'] or 0.00

    @property
    def aggregate_generation_today(self):
        return self.deye_devices.aggregate(models.Sum('today_generation'))['today_generation__sum'] or 0.00

    @property
    def aggregate_generation_total(self):
        return self.deye_devices.aggregate(models.Sum('total_generation'))['total_generation__sum'] or 0.00

    def get_full_name(self):
        """Returns the full name including middle name if it exists"""
        names = [self.user.first_name, self.middle_name, self.user.last_name]
        return " ".join([n for n in names if n])

    def __str__(self):
        return self.user.email or self.user.username


class CustomerUpdate(models.Model):
    """Model to store updates for a customer"""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='updates')
    date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()

    def __str__(self):
        return f"Update for {self.customer} by {self.user}"


class OTP(models.Model):
    """Model for storing OTP codes"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    otp_type = models.CharField(max_length=20, choices=[
        ('phone', 'Phone'),
        ('email', 'Email'),
        ('registration', 'Registration'),
    ])

    def __str__(self):
        return f"OTP for {self.user.email} - {self.otp_code}"


class QuoteRequest(models.Model):
    """Model for storing quote requests"""
    reference = models.CharField(max_length=100, unique=True, blank=True, null=True)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    business_name = models.CharField(max_length=200, blank=True, null=True)
    industry = models.CharField(max_length=100, blank=True, null=True)
    energy_consumption = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    county = models.CharField(max_length=100, blank=True, null=True)
    town = models.CharField(max_length=100, blank=True, null=True)
    area = models.CharField(max_length=100, blank=True, null=True)
    roof_type = models.CharField(max_length=100, blank=True, null=True)
    type = models.CharField(max_length=100, default="Individual") # For table in applications.html
    installer = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=100, default="New")
    additional_info = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.reference:
            import uuid
            self.reference = f"APP-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Quote request from {self.name} ({self.reference})"


class ApplicationUpdate(models.Model):
    """Model to store updates for a quote request/application"""
    quote_request = models.ForeignKey(QuoteRequest, on_delete=models.CASCADE, related_name='updates')
    date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()

    def __str__(self):
        return f"Update for {self.quote_request.name} by {self.user}"


class ContactMessage(models.Model):
    """Model for storing contact messages"""
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Contact from {self.name}"


class JobApplication(models.Model):
    """Model for storing job applications"""
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    position = models.CharField(max_length=100)
    experience = models.CharField(max_length=100)
    cover_letter = models.TextField(blank=True, null=True)
    resume = models.FileField(upload_to='resumes/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Job application from {self.name} for {self.position}"


class NewsletterSubscriber(models.Model):
    """Model for storing newsletter subscribers"""
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


class Payment(models.Model):
    """Model for storing customer payments"""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    billing_type = models.CharField(max_length=100)
    payment_mode = models.CharField(max_length=100)
    site_name = models.CharField(max_length=200)
    reference = models.CharField(max_length=100)
    status = models.CharField(max_length=50)

    # Detailed information for the view page
    mpesa_reference = models.CharField(max_length=100, blank=True, null=True)
    payment_time = models.CharField(max_length=50, blank=True, null=True)  # Using string to match image format like "12:24"
    payment_number = models.CharField(max_length=20, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.reference} - {self.amount}"


class Wallet(models.Model):
    """Model to store customer wallet information"""
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='wallet')
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    available_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet for {self.customer.user.email or self.customer.user.username}"


class Transaction(models.Model):
    """Model to store wallet transactions"""
    TRANSACTION_TYPES = [
        ('top_up', 'Top Up'),
        ('transfer', 'Transfer'),
        ('payment', 'Payment'),
    ]

    ORIGINATORS = [
        ('customer', 'Customer'),
        ('bank', 'Bank'),
        ('vegrid', 'Vegrid'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_date = models.DateField(auto_now_add=True)
    transaction_time = models.TimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    credit_debit = models.CharField(max_length=10, choices=[('credit', 'Credit'), ('debit', 'Debit')])
    transaction_type = models.CharField(max_length=50)  # Mobile Money/Bank/etc.
    originator = models.CharField(max_length=50, choices=ORIGINATORS)
    reference = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')

    # Details from images
    source_destination = models.CharField(max_length=100, blank=True, null=True)  # e.g. Mpesa, Bank Name
    source_destination_number = models.CharField(max_length=50, blank=True, null=True)
    transaction_bank = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} ({self.status})"


class DeyeDevice(models.Model):
    """Model to store DeyeCloud device information for customers"""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='deye_devices')
    name = models.CharField(max_length=100, default="My Solar Site")
    device_sn = models.CharField(max_length=100, unique=True)
    station_id = models.CharField(max_length=100, blank=True, null=True)
    deye_username = models.CharField(max_length=100, blank=True, null=True)
    deye_password = models.CharField(max_length=100, blank=True, null=True)
    
    # New fields for site management
    county = models.CharField(max_length=100, default="Nairobi")
    town = models.CharField(max_length=100, default="Nairobi")
    country = models.CharField(max_length=100, default="Kenya")
    area = models.CharField(max_length=100, default="Runda")
    service_area = models.CharField(max_length=100, blank=True, null=True)
    time_zone = models.CharField(max_length=100, default="UTC")
    latitude = models.DecimalField(max_digits=12, decimal_places=9, blank=True, null=True)
    longitude = models.DecimalField(max_digits=12, decimal_places=9, blank=True, null=True)
    location_address = models.CharField(max_length=255, blank=True, null=True)
    
    # System Information
    rating = models.DecimalField(max_digits=10, decimal_places=2, default=5.0) # kVA
    inverter_brand = models.CharField(max_length=100, blank=True, null=True)
    inverter_model = models.CharField(max_length=100, blank=True, null=True)
    installed_capacity = models.DecimalField(max_digits=10, decimal_places=2, default=0.0) # kWp
    battery_capacity = models.DecimalField(max_digits=10, decimal_places=2, default=0.0) # kWh
    battery_brand = models.CharField(max_length=100, blank=True, null=True)
    
    # Installation Information
    installer = models.CharField(max_length=100, blank=True, null=True)
    installation_engineer = models.CharField(max_length=100, blank=True, null=True)
    installation_date = models.DateTimeField(blank=True, null=True)
    
    # Commission Information
    owner = models.CharField(max_length=100, default="Customer")
    financier_type = models.CharField(max_length=50, choices=[('Bank', 'Bank'), ('Customer', 'Customer')], default='Customer')
    financier = models.CharField(max_length=100, blank=True, null=True)
    currency = models.CharField(max_length=20, default="KES")
    service_rep = models.CharField(max_length=100, blank=True, null=True)

    generation = models.DecimalField(max_digits=10, decimal_places=2, default=0.0) # kW
    storage = models.DecimalField(max_digits=10, decimal_places=2, default=0.0) # kW/kWh
    battery_soc = models.DecimalField(max_digits=5, decimal_places=2, default=0.0, blank=True, null=True)
    grid_imports = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    grid_export = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    load = models.DecimalField(max_digits=10, decimal_places=2, default=0.0) # Consumption (kW)
    total_consumption = models.DecimalField(max_digits=12, decimal_places=2, default=0.0) # kWh (Total)
    today_consumption = models.DecimalField(max_digits=12, decimal_places=2, default=0.0) # kWh (Today)
    today_generation = models.DecimalField(max_digits=12, decimal_places=2, default=0.0) # kWh (Today)
    total_generation = models.DecimalField(max_digits=12, decimal_places=2, default=0.0) # kWh (Total)
    status = models.CharField(max_length=50, default="Online")

    # Store token and expiry to minimize API calls
    last_token = models.TextField(blank=True, null=True)
    token_expires_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.device_sn})"

    def sync_consumption_data(self):
        """Fetch and update consumption data from Deye API"""
        from vegrid_app.services.deye_service import DeyeService
        service = DeyeService()
        
        try:
            # Try to get station ID or use device SN
            station_id = getattr(service, 'get_station_id_by_device_sn', lambda x: x)(self.device_sn) or self.device_sn
            latest_resp = service.get_station_latest(station_id)
            
            if latest_resp and latest_resp.get('code') in [0, "0", "1000000"]:
                data = latest_resp.get('data', {})
                self.today_consumption = float(data.get('consumptionToday', self.today_consumption))
                self.today_generation = float(data.get('generationToday', self.today_generation))
                self.total_generation = float(data.get('generationTotal', self.total_generation))
                
                # If specific consumption metrics are available in detail
                detail_resp = service.get_station_detail_by_id(station_id)
                if detail_resp and detail_resp.get('code') in [0, "0", "1000000"]:
                    detail_data = detail_resp.get('data', {})
                    # Some APIs provide consumption directly
                    if 'consumptionTotal' in detail_data:
                        self.total_consumption = float(detail_data['consumptionTotal'])
                
                self.save()
                return True
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error syncing consumption for {self.device_sn}: {e}")
        
        return False

    def get_token(self):
        """Get a valid token, refreshing if necessary"""
        from vegrid_app.deye_api import DeyeAPI
        api = DeyeAPI()
        
        # Check if we have a valid token
        if self.last_token and self.token_expires_at and self.token_expires_at > timezone.now():
            return self.last_token
            
        # Refresh token
        username = self.deye_username
        password = self.deye_password
        
        if not username or not password:
            raise Exception("Missing Deye credentials for this device.")
            
        result = api.get_token(username=username, password=password, hash_type='sha256')
        if result.get('code') != 0:
            # Fallback to MD5 if SHA256 fails
            result = api.get_token(username=username, password=password, hash_type='md5')
            
        if result.get('code') == 0:
            self.last_token = result['data']['accessToken']
            expires_in = result['data'].get('expiresIn', 86400)
            self.token_expires_at = timezone.now() + timedelta(seconds=expires_in - 300)
            self.save()
            return self.last_token
        
        # Handle specific error message from Deye
        error_msg = result.get('msg', 'Unknown Deye API error')
        if isinstance(error_msg, str) and error_msg.startswith('{'):
            try:
                error_data = json.loads(error_msg)
                error_msg = error_data.get('error', error_msg)
            except:
                pass
        raise Exception(f"Deye API error: {error_msg}")

    def get_realtime_data(self):
        """Fetch real-time data from DeyeCloud"""
        token = self.get_token()
        if not token:
            raise Exception("Failed to obtain Deye API token.")
            
        from vegrid_app.deye_api import DeyeAPI
        api = DeyeAPI()
        result = api.get_device_realtime(token, self.device_sn)
        if result.get('code') == 0:
            return result['data']
        
        error_msg = result.get('msg', 'Unknown Deye API error')
        if isinstance(error_msg, str) and error_msg.startswith('{'):
            try:
                error_data = json.loads(error_msg)
                error_msg = error_data.get('error', error_msg)
            except:
                pass
        raise Exception(f"Deye API error: {error_msg}")


class DeyeDeviceImage(models.Model):
    """Model to store site images"""
    device = models.ForeignKey(DeyeDevice, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='site_images/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.device.name} - {self.id}"


class PartnerInvoice(models.Model):
    """Model to store partner invoices"""
    date = models.DateField(auto_now_add=True)
    reference = models.CharField(max_length=100, unique=True)
    invoice_type = models.CharField(max_length=100)  # Dispatch, Delivery, Site Survey, etc.
    payee_type = models.CharField(max_length=100)  # Distributor, Dealer, Installer, etc.
    name = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()
    status = models.CharField(max_length=50)

    def __str__(self):
        return f"Invoice {self.reference} - {self.name}"


class PartnerInvoiceUpdate(models.Model):
    """Model to store updates for a partner invoice"""
    invoice = models.ForeignKey(PartnerInvoice, on_delete=models.CASCADE, related_name='updates')
    date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()

    def __str__(self):
        return f"Update for {self.invoice.reference} by {self.user}"


class RFQ(models.Model):
    """Model to store RFQs"""
    date = models.DateField(auto_now_add=True)
    number = models.CharField(max_length=100, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    closing_date = models.DateField()
    town = models.CharField(max_length=100)
    area = models.CharField(max_length=100)
    installer = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=50)

    def __str__(self):
        return f"RFQ {self.number} - {self.customer}"


class RFQUpdate(models.Model):
    """Model to store updates for an RFQ"""
    rfq = models.ForeignKey(RFQ, on_delete=models.CASCADE, related_name='updates')
    date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()

    def __str__(self):
        return f"Update for {self.rfq.number} by {self.user}"


class RFQItem(models.Model):
    """Model to store items within an RFQ"""
    rfq = models.ForeignKey(RFQ, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=255)
    quantity = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.description} for {self.rfq.number}"


class Dispatch(models.Model):
    """Model to store dispatches"""
    date = models.DateField(auto_now_add=True)
    reference = models.CharField(max_length=100, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    distributor = models.CharField(max_length=100)
    transporter = models.CharField(max_length=100)
    dealer = models.CharField(max_length=100)
    installer = models.CharField(max_length=100)
    status = models.CharField(max_length=50)

    def __str__(self):
        return f"Dispatch {self.reference} - {self.customer}"


class DispatchUpdate(models.Model):
    """Model to store updates for a dispatch"""
    dispatch = models.ForeignKey(Dispatch, on_delete=models.CASCADE, related_name='updates')
    date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()

    def __str__(self):
        return f"Update for {self.dispatch.reference} by {self.user}"


class PackingListItem(models.Model):
    """Model to store packing list items for a dispatch"""
    dispatch = models.ForeignKey(Dispatch, on_delete=models.CASCADE, related_name='packing_list')
    item = models.CharField(max_length=100)
    manufacturer = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    quantity = models.IntegerField()
    status = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.item} for Dispatch {self.dispatch.reference}"


class Incident(models.Model):
    """Model to store incidents"""
    date = models.DateTimeField(auto_now_add=True)
    sender = models.CharField(max_length=100)
    incident_type = models.CharField(max_length=100)  # Service, Payment, Billing, etc.
    recipient_type = models.CharField(max_length=100)
    recipient = models.CharField(max_length=100)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, blank=True, null=True)
    status = models.CharField(max_length=50)
    reference = models.CharField(max_length=100, unique=True, blank=True, null=True)

    def __str__(self):
        return f"Incident {self.reference} - {self.incident_type}"


class IncidentUpdate(models.Model):
    """Model to store updates for an incident"""
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='updates')
    date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()

    def __str__(self):
        return f"Update for {self.incident.reference} by {self.user}"


class Alert(models.Model):
    """Model to store system alerts"""
    date = models.DateTimeField()
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    site = models.CharField(max_length=100)
    source = models.CharField(max_length=100)  # Inverter, Battery, Panel, etc.
    alert_type = models.CharField(max_length=100)
    severity = models.CharField(max_length=50)  # Low, Medium, High, Critical
    status = models.CharField(max_length=50)
    message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Alert {self.severity} from {self.source} - {self.customer}"


class AlertUpdate(models.Model):
    """Model to store updates for an alert"""
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name='updates')
    date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()

    def __str__(self):
        return f"Update for {self.alert} by {self.user}"


class TeamMember(models.Model):
    """Model to store team members"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='team_member', null=True, blank=True)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100)
    id_number = models.CharField(max_length=100, blank=True, null=True)
    pin_number = models.CharField(max_length=100, blank=True, null=True)
    contact = models.CharField(max_length=20)
    email = models.EmailField(unique=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    town = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    role = models.CharField(max_length=100)
    registration_type = models.CharField(max_length=100, blank=True, null=True)
    registration_number = models.CharField(max_length=100, blank=True, null=True)
    qualification = models.CharField(max_length=100, blank=True, null=True)
    documents = models.FileField(upload_to='team_docs/', blank=True, null=True)
    photo = models.ImageField(upload_to='team_photos/', blank=True, null=True)
    status = models.CharField(max_length=50, default="Active")

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"


class TeamMemberUpdate(models.Model):
    """Model to store updates for a team member"""
    member = models.ForeignKey(TeamMember, on_delete=models.CASCADE, related_name='updates')
    date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()

    def __str__(self):
        return f"Update for {self.member.email} by {self.user}"


class Notification(models.Model):
    """Model to store system notifications"""
    date = models.DateTimeField(auto_now_add=True)
    sender = models.CharField(max_length=100, default="VEGRID ADMIN")
    recipient_type = models.CharField(max_length=100, choices=[('all', 'All Customers'), ('individual', 'Individual'), ('group', 'Group')], default='individual')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, blank=True, null=True)
    recipient_name = models.CharField(max_length=200, blank=True, null=True)
    notification_type = models.CharField(max_length=100, blank=True, null=True) # Service, Payment, etc.
    message = models.TextField()
    status = models.CharField(max_length=50, choices=[('read', 'Read'), ('unread', 'Unread')], default='unread')
    reference = models.CharField(max_length=100, unique=True, blank=True, null=True)

    def __str__(self):
        return f"Notification {self.reference} for {self.recipient_name or self.customer}"


class NotificationUpdate(models.Model):
    """Model to store updates for a notification"""
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='updates')
    date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()

    def __str__(self):
        return f"Update for {self.notification.reference} by {self.user}"


class CustomerBilling(models.Model):
    """Model to store customer billings"""
    date = models.DateField(auto_now_add=True)
    reference = models.CharField(max_length=100, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    billing_type = models.CharField(max_length=100, blank=True, null=True)  # Monthly Fee, Installation, etc.
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    due_date = models.DateField()
    status = models.CharField(max_length=50, choices=[('paid', 'Paid'), ('pending', 'Pending'), ('overdue', 'Overdue')], default='pending')

    def __str__(self):
        return f"Billing {self.reference} for {self.customer}"


class BillingUpdate(models.Model):
    """Model to store updates for a billing"""
    billing = models.ForeignKey(CustomerBilling, on_delete=models.CASCADE, related_name='updates')
    date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()

    def __str__(self):
        return f"Update for {self.billing.reference} by {self.user}"
