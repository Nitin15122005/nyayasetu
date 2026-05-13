import requests

url = "http://localhost:8001/api/evidence"
files = {'file': ('test.jpg', b'fake image data', 'image/jpeg')}
data = {
    'complainant_name': 'Test User',
    'complainant_phone': '9876543210',
    'complainant_address': 'Test Address',
    'incident_brief': 'Test Brief',
    'incident_date': '2026-05-13',
    'police_station': 'Test PS'
}

r = requests.post(url, files=files, data=data)
print(f"Status: {r.status_code}")
print(f"Response: {r.json()}")
