with open('c:/Users/HomePC/Downloads/vegrid/vegrid_app/services/deye_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Search for cleanup_alert_names method
if 'cleanup_alert_names' in content:
    print("Found cleanup_alert_names method")
    index = content.find('cleanup_alert_names')
    # Show 100 characters before and after
    print("\n" + content[max(0, index - 20):index + 200])
else:
    print("cleanup_alert_names not found, searching for alert processing methods")
    
# Search for alert name formatting methods
for term in ['alert.*name', 'format.*alert', 'parse.*alert', 'get.*alerts']:
    import re
    matches = re.findall(term, content, re.IGNORECASE)
    if matches:
        print(f"\nFound matches for '{term}': {len(matches)} matches")
