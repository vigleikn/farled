import os
import sys
import requests
from datetime import datetime, timezone


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


def fetch_ferry_positions(ferry_list: list, bearer_token: str) -> list:
    """Fetch current positions for ferries from Barentswatch API"""
    try:
        headers = {'Authorization': f'Bearer {bearer_token}'}
        url = "https://live.ais.barentswatch.no/v1/latest/combined"

        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code != 200:
            print(f"[ADVARSEL] Barentswatch API returned {response.status_code}", file=sys.stderr)
            return []

        vessel_data = response.json()
        ferry_positions = []

        # Create MMSI lookup for ferries
        ferry_mmsis = {ferry['mmsi']: ferry for ferry in ferry_list if ferry.get('mmsi')}

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

    except Exception as e:
        print(f"[ADVARSEL] Ferry position fetch failed: {e}", file=sys.stderr)
        return []
