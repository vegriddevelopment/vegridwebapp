from django.contrib import admin
from .models import QuoteRequest, ContactMessage, JobApplication, NewsletterSubscriber, Customer, Payment, Wallet, Transaction, DeyeDevice, Alert, DeyeDeviceImage


class DeyeDeviceImageInline(admin.TabularInline):
    model = DeyeDeviceImage
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ('date', 'amount', 'site_name', 'reference', 'status')
    readonly_fields = ('date',)


class AlertInline(admin.TabularInline):
    model = Alert
    extra = 0
    fields = ('date', 'site', 'alert_type', 'severity', 'status')
    readonly_fields = ('date',)


class DeyeDeviceInline(admin.TabularInline):
    model = DeyeDevice
    extra = 0
    fields = ('name', 'device_sn', 'status', 'created_at')
    readonly_fields = ('created_at',)
    verbose_name = "Site"
    verbose_name_plural = "Sites"


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('customer_id', 'user', 'get_full_name', 'phone_number', 'registration_type', 'is_verified', 'aggregate_rating', 'aggregate_storage')
    search_fields = ('customer_id', 'user__username', 'user__email', 'phone_number')
    list_filter = ('registration_type', 'is_verified')
    inlines = [DeyeDeviceInline, AlertInline, PaymentInline]
    readonly_fields = ('aggregate_rating', 'aggregate_storage')
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('user', 'customer_id', 'middle_name', 'id_number', 'pin_number', 'phone_number', 'registration_type', 'passport_photo', 'is_verified')
        }),
        ('Site Information', {
            'fields': ('address', 'county', 'town', 'country', 'area', 'aggregate_rating', 'aggregate_storage')
        }),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('reference', 'customer', 'amount', 'date', 'status')
    search_fields = ('reference', 'customer__user__username', 'mpesa_reference')
    list_filter = ('status', 'billing_type', 'payment_mode')


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('customer', 'current_balance', 'available_balance', 'updated_at')
    search_fields = ('customer__user__username', 'customer__user__email')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('reference', 'wallet', 'amount', 'credit_debit', 'status', 'transaction_date')
    search_fields = ('reference', 'wallet__customer__user__username', 'transaction_type')
    list_filter = ('status', 'credit_debit', 'originator')


@admin.register(DeyeDevice)
class DeyeDeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'device_sn', 'customer', 'status', 'rating', 'generation', 'storage', 'load', 'created_at')
    search_fields = ('name', 'device_sn', 'customer__user__username', 'customer__user__email', 'county', 'town', 'area')
    list_filter = ('status', 'country', 'county', 'created_at')
    readonly_fields = ('created_at', 'updated_at', 'last_token', 'token_expires_at')
    inlines = [DeyeDeviceImageInline]
    fieldsets = (
        ('Site Identification', {
            'fields': ('customer', 'name', 'device_sn', 'status')
        }),
        ('Location Information', {
            'fields': ('location_address', 'area', 'town', 'county', 'country', 'service_area', 'latitude', 'longitude', 'time_zone')
        }),
        ('Technical Specifications', {
            'fields': ('rating', 'inverter_brand', 'inverter_model', 'installed_capacity', 'battery_capacity', 'battery_brand', 'generation', 'storage', 'load', 'grid_imports', 'grid_export')
        }),
        ('Installation & Commission', {
            'fields': ('installer', 'installation_engineer', 'installation_date', 'owner', 'currency', 'service_rep')
        }),
        ('API Credentials', {
            'classes': ('collapse',),
            'fields': ('deye_username', 'deye_password', 'last_token', 'token_expires_at')
        }),
        ('System Info', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('date', 'customer', 'site', 'alert_type', 'severity', 'status')
    search_fields = ('customer__user__username', 'site', 'alert_type', 'message')
    list_filter = ('severity', 'status', 'alert_type', 'date')


@admin.register(QuoteRequest)
class QuoteRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'business_name', 'created_at')
    search_fields = ('name', 'email', 'business_name')
    list_filter = ('created_at', 'industry')


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'subject', 'created_at')
    search_fields = ('name', 'email', 'subject')
    list_filter = ('created_at',)


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'position', 'created_at')
    search_fields = ('name', 'email', 'position')
    list_filter = ('created_at', 'position')


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'subscribed_at')
    search_fields = ('email',)
    list_filter = ('subscribed_at',)
