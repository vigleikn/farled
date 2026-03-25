# scripts/process_ferries.py
import csv
import os
import requests
from datetime import datetime, timezone

def validate_mmsi(mmsi_str):
    """Validate 9-digit MMSI format"""
    if not mmsi_str or mmsi_str.strip() == '':
        return False
    try:
        mmsi = int(mmsi_str)
        return 100000000 <= mmsi <= 999999999
    except ValueError:
        return False

def validate_norwegian_waters(lat, lon):
    """Validate coordinates are within Norwegian waters (58°-81°N, 4°-32°E)"""
    return 58 <= lat <= 81 and 4 <= lon <= 32

def process_ferry_csv(csv_path):
    """Process ferry CSV and return valid entries"""
    ferries = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('Navn', '').strip()
            mmsi = row.get('MMSI-nummer', '').strip()

            if name and validate_mmsi(mmsi):
                ferries.append({
                    'name': name,
                    'imo': row.get('IMO-nummer', '').strip(),
                    'mmsi': mmsi
                })
    return ferries

def get_api_headers():
    """Get API headers with authentication token"""
    token = os.environ.get('BARENTSWATCH_API_TOKEN')
    if not token:
        raise ValueError("BARENTSWATCH_API_TOKEN environment variable required")
    return {'Authorization': f'Bearer {token}'}

def validate_timestamp(timestamp_str, max_age_hours=24):
    """Validate position timestamp is within max_age_hours"""
    if not timestamp_str:
        return True  # Allow missing timestamps

    try:
        # Parse ISO format timestamp
        if timestamp_str.endswith('Z'):
            timestamp_str = timestamp_str[:-1] + '+00:00'

        pos_time = datetime.fromisoformat(timestamp_str)
        now = datetime.now(timezone.utc)

        # Ensure both timestamps have timezone info
        if pos_time.tzinfo is None:
            pos_time = pos_time.replace(tzinfo=timezone.utc)

        age_hours = (now - pos_time).total_seconds() / 3600
        return age_hours <= max_age_hours
    except:
        return True  # Allow on parse errors

def process_ferry_position(mmsi, api_data):
    """Process and validate ferry position data"""
    if not api_data or 'latitude' not in api_data or 'longitude' not in api_data:
        return None

    lat, lon = api_data['latitude'], api_data['longitude']
    timestamp = api_data.get('timestamp')

    # Validate coordinates and timestamp
    if not validate_norwegian_waters(lat, lon):
        return None
    if not validate_timestamp(timestamp):
        return None

    return {
        'lat': lat,
        'lon': lon,
        'timestamp': timestamp
    }

def get_single_ferry_position(mmsi):
    """Get single ferry position from Barentswatch API"""
    try:
        headers = get_api_headers()
        url = f"https://www.barentswatch.no/bwapi/v1/ais/latest/{mmsi}"

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 401:
            raise ValueError("API authentication failed - check token")
        elif response.status_code != 200:
            return None

        return response.json()
    except requests.RequestException:
        return None