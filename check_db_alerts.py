import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.models import Alert
alerts = Alert.objects.all().order_by('-date')[:50]
print("--- LAST 50 ALERTS ---")
for a in alerts:
    print(f"ID: {a.id} | Site: {a.site} | Status: {a.status} | Type: {a.alert_type}")

