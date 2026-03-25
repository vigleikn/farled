import os
import requests
from typing import Optional


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

    response = requests.post(token_url, data=data, timeout=30)

    if response.status_code != 200:
        raise ValueError(f"Token request failed: {response.status_code}")

    token_data = response.json()
    return token_data['access_token']
