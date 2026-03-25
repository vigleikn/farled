# scripts/process_ferries.py
import csv
import os

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