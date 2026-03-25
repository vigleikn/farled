import os
import sys
import csv
import requests
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any


def get_barentswatch_token() -> str:
    """Get OAuth2 bearer token from Barentswatch API"""
    client_id = os.environ.get('BARENTSWATCH_CLIENT_ID')
    client_secret = os.environ.get('BARENTSWATCH_CLIENT_SECRET')

    if not client_id:
        raise ValueError("BARENTSWATCH_CLIENT_ID environment variable required")
    if not client_secret:
        raise ValueError("BARENTSWATCH_CLIENT_SECRET environment variable required")

    token_url = 'https://id.barentswatch.no/connect/token'
    data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'ais'
    }

    try:
        response = requests.post(token_url, data=data, timeout=30)
    except requests.exceptions.Timeout:
        raise RuntimeError("Token request timed out after 30 seconds")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Network error while requesting token: {str(e)}")

    if response.status_code != 200:
        try:
            error_details = response.json()
            error_msg = error_details.get('error_description', str(error_details))
        except Exception:
            error_msg = response.text or "No error details available"
        raise RuntimeError(
            f"Token request failed with status {response.status_code}: {error_msg}"
        )

    try:
        token_data = response.json()
    except ValueError as e:
        raise RuntimeError(f"Failed to parse token response as JSON: {str(e)}")

    if 'access_token' not in token_data:
        raise RuntimeError(
            f"Invalid token response: missing 'access_token' field. "
            f"Response keys: {list(token_data.keys())}"
        )

    return token_data['access_token']


def validate_norwegian_waters(lat: float, lon: float) -> bool:
    """Validate coordinates are within Norwegian waters"""
    return 58 <= lat <= 81 and 4 <= lon <= 32


def validate_mmsi(mmsi_str: str) -> bool:
    """Validate 9-digit MMSI format"""
    if not mmsi_str or mmsi_str.strip() == '':
        return False
    try:
        mmsi = int(mmsi_str)
        return 100000000 <= mmsi <= 999999999
    except ValueError:
        return False


def load_ferry_data_from_csv(csv_path: Path) -> List[Dict[str, Any]]:
    """Load and validate ferry data from CSV file"""
    ferries = []

    if not csv_path.exists():
        print(f"[ADVARSEL] Ferry CSV not found: {csv_path}", file=sys.stderr)
        return []

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            # Validate that required columns exist
            if reader.fieldnames is None or not all(
                col in reader.fieldnames for col in ['Navn', 'MMSI-nummer']
            ):
                print(
                    f"[ADVARSEL] CSV missing required columns. Found: {reader.fieldnames}",
                    file=sys.stderr
                )
                return []

            for row in reader:
                name = (row.get('Navn') or '').strip()
                mmsi = (row.get('MMSI-nummer') or '').strip()

                if name and validate_mmsi(mmsi):
                    ferries.append({
                        'name': name,
                        'imo': (row.get('IMO-nummer') or '').strip(),
                        'mmsi': mmsi
                    })
    except UnicodeDecodeError as e:
        print(f"[ADVARSEL] CSV encoding error: {e}", file=sys.stderr)
        return []
    except csv.Error as e:
        print(f"[ADVARSEL] CSV parsing error: {e}", file=sys.stderr)
        return []
    except IOError as e:
        print(f"[ADVARSEL] Error reading ferry CSV file: {e}", file=sys.stderr)
        return []

    return ferries


def fetch_ferry_positions(ferry_list: List[Dict[str, Any]], bearer_token: str) -> List[Dict[str, Any]]:
    """Fetch current positions for ferries from Barentswatch API"""
    try:
        headers = {'Authorization': f'Bearer {bearer_token}'}
        url = "https://live.ais.barentswatch.no/v1/latest/combined"

        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code != 200:
            print(f"[ADVARSEL] Barentswatch API returned {response.status_code}", file=sys.stderr)
            return []

        try:
            vessel_data = response.json()
        except ValueError as e:
            print(f"[ADVARSEL] Failed to parse vessel data as JSON: {e}", file=sys.stderr)
            return []

        ferry_positions = []

        # Create MMSI lookup for ferries with consistent string conversion
        ferry_mmsis = {str(ferry.get('mmsi', '')): ferry for ferry in ferry_list if ferry.get('mmsi')}

        # Find ferries in vessel data
        for vessel in vessel_data:
            mmsi = str(vessel.get('mmsi', ''))

            if mmsi in ferry_mmsis:
                ferry = ferry_mmsis[mmsi]
                lat = vessel.get('latitude')
                lon = vessel.get('longitude')
                timestamp = vessel.get('timestamp')

                if lat is not None and lon is not None and validate_norwegian_waters(lat, lon):
                    ferry_positions.append({
                        'name': ferry['name'],
                        'imo': ferry.get('imo', ''),
                        'mmsi': mmsi,
                        'lat': lat,
                        'lon': lon,
                        'lastUpdate': timestamp
                    })

        return ferry_positions

    except requests.exceptions.Timeout:
        print(f"[ADVARSEL] Ferry position fetch timed out", file=sys.stderr)
        return []
    except requests.exceptions.RequestException as e:
        print(f"[ADVARSEL] Ferry position fetch network error: {e}", file=sys.stderr)
        return []
