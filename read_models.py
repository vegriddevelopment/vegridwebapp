with open('c:/Users/HomePC/Downloads/vegrid/vegrid_app/models.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("Looking for Alert model...")
found_alert = False
for i, line in enumerate(lines):
    if 'class Alert' in line:
        found_alert = True
        print(f"\nAlert model found at line {i+1}")
        # Print next 50 lines
        for j in range(i, min(i+50, len(lines))):
            print(f"{j+1}: {lines[j]}", end='')

if not found_alert:
    print("\nAlert model not found in models.py")
    # Check if it's imported from somewhere else
    for i, line in enumerate(lines):
        if 'Alert' in line and 'from' in line:
            print(f"\nAlert imported at line {i+1}: {line}")
