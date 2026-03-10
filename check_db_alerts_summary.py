import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()
from vegrid_app.models import Alert
print(f"Total alerts in DB: {Alert.objects.count()}")
for a in Alert.objects.all().order_by('-date')[:10]:
    print(f"- [{a.date}] {a.severity} - {a.alert_type} at {a.site} ({a.status})")
