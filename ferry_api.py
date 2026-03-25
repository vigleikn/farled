import os
import requests


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
