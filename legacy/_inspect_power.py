import requests, json, sys
lat, lon, year = 53.4285, 14.5528, 2024
url = 'https://power.larc.nasa.gov/api/temporal/monthly/point'
params = {
    'parameters': 'T2M,PRECTOT',
    'community': 'RE',
    'latitude': lat,
    'longitude': lon,
    'start': year,
    'end': year,
    'format': 'JSON'
}
print('Request URL:', url)
print('Params:', params)
resp = requests.get(url, params=params, timeout=60)
print('Status:', resp.status_code)
try:
    data = resp.json()
except Exception as e:
    print('Failed to parse JSON:', e)
    print(resp.text[:1000])
    sys.exit(1)
print('Top-level keys:', list(data.keys()))
if 'properties' in data:
    print('properties keys:', list(data['properties'].keys()))
    if 'parameter' in data['properties']:
        print('parameter subkeys:', list(data['properties']['parameter'].keys()))
if 'parameters' in data:
    print('parameters block keys:', list(data['parameters'].keys()))
# Dump truncated JSON
print('Truncated JSON:\n', json.dumps(data, indent=2)[:4000])
