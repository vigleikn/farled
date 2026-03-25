import os
import pytest
from unittest.mock import Mock, patch
import requests

def test_get_barentswatch_token_success():
    """Test successful token retrieval from Barentswatch API"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'access_token': 'test_bearer_token_123',
        'expires_in': 3600
    }

    with patch('requests.post', return_value=mock_response):
        with patch.dict(os.environ, {
            'BARENTSWATCH_CLIENT_ID': 'test_id',
            'BARENTSWATCH_CLIENT_SECRET': 'test_secret'
        }):
            from ferry_api import get_barentswatch_token
            token = get_barentswatch_token()
            assert token == 'test_bearer_token_123'

def test_get_barentswatch_token_missing_client_id():
    """Test error handling for missing BARENTSWATCH_CLIENT_ID"""
    with patch.dict(os.environ, {}, clear=True):
        from ferry_api import get_barentswatch_token
        with pytest.raises(ValueError, match="BARENTSWATCH_CLIENT_ID"):
            get_barentswatch_token()

def test_get_barentswatch_token_missing_client_secret():
    """Test error handling for missing BARENTSWATCH_CLIENT_SECRET"""
    with patch.dict(os.environ, {'BARENTSWATCH_CLIENT_ID': 'test_id'}, clear=True):
        from ferry_api import get_barentswatch_token
        with pytest.raises(ValueError, match="BARENTSWATCH_CLIENT_SECRET"):
            get_barentswatch_token()

def test_get_barentswatch_token_http_400_error():
    """Test error handling for HTTP 400 Bad Request"""
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.json.return_value = {
        'error': 'invalid_client',
        'error_description': 'Client credentials are invalid'
    }

    with patch('requests.post', return_value=mock_response):
        with patch.dict(os.environ, {
            'BARENTSWATCH_CLIENT_ID': 'test_id',
            'BARENTSWATCH_CLIENT_SECRET': 'test_secret'
        }):
            from ferry_api import get_barentswatch_token
            with pytest.raises(RuntimeError, match="Token request failed with status 400"):
                get_barentswatch_token()

def test_get_barentswatch_token_http_500_error():
    """Test error handling for HTTP 500 Internal Server Error"""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = 'Internal Server Error'
    mock_response.json.side_effect = ValueError("No JSON")

    with patch('requests.post', return_value=mock_response):
        with patch.dict(os.environ, {
            'BARENTSWATCH_CLIENT_ID': 'test_id',
            'BARENTSWATCH_CLIENT_SECRET': 'test_secret'
        }):
            from ferry_api import get_barentswatch_token
            with pytest.raises(RuntimeError, match="Token request failed with status 500"):
                get_barentswatch_token()

def test_get_barentswatch_token_network_timeout():
    """Test error handling for network timeout"""
    with patch('requests.post', side_effect=requests.exceptions.Timeout("Connection timed out")):
        with patch.dict(os.environ, {
            'BARENTSWATCH_CLIENT_ID': 'test_id',
            'BARENTSWATCH_CLIENT_SECRET': 'test_secret'
        }):
            from ferry_api import get_barentswatch_token
            with pytest.raises(RuntimeError, match="Token request timed out"):
                get_barentswatch_token()

def test_get_barentswatch_token_network_error():
    """Test error handling for general network errors"""
    with patch('requests.post', side_effect=requests.exceptions.ConnectionError("Connection refused")):
        with patch.dict(os.environ, {
            'BARENTSWATCH_CLIENT_ID': 'test_id',
            'BARENTSWATCH_CLIENT_SECRET': 'test_secret'
        }):
            from ferry_api import get_barentswatch_token
            with pytest.raises(RuntimeError, match="Network error while requesting token"):
                get_barentswatch_token()

def test_get_barentswatch_token_malformed_json():
    """Test error handling for malformed JSON response"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("Invalid JSON")

    with patch('requests.post', return_value=mock_response):
        with patch.dict(os.environ, {
            'BARENTSWATCH_CLIENT_ID': 'test_id',
            'BARENTSWATCH_CLIENT_SECRET': 'test_secret'
        }):
            from ferry_api import get_barentswatch_token
            with pytest.raises(RuntimeError, match="Failed to parse token response as JSON"):
                get_barentswatch_token()

def test_get_barentswatch_token_missing_access_token():
    """Test error handling for missing access_token in response"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'expires_in': 3600
    }

    with patch('requests.post', return_value=mock_response):
        with patch.dict(os.environ, {
            'BARENTSWATCH_CLIENT_ID': 'test_id',
            'BARENTSWATCH_CLIENT_SECRET': 'test_secret'
        }):
            from ferry_api import get_barentswatch_token
            with pytest.raises(RuntimeError, match="missing 'access_token' field"):
                get_barentswatch_token()

def test_fetch_ferry_positions_success():
    """Test successful ferry position fetching and processing"""
    mock_vessels = [
        {
            'mmsi': 257741000,
            'latitude': 69.123,
            'longitude': 16.456,
            'timestamp': '2026-03-25T10:30:00Z'
        },
        {
            'mmsi': 999999999,  # Not a ferry
            'latitude': 60.0,
            'longitude': 5.0,
            'timestamp': '2026-03-25T10:30:00Z'
        }
    ]

    ferry_csv_data = [
        {'name': 'BARØY', 'imo': '9607394', 'mmsi': '257741000'}
    ]

    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_vessels
        mock_get.return_value = mock_response

        from ferry_api import fetch_ferry_positions
        positions = fetch_ferry_positions(ferry_csv_data, 'test_token')

        assert len(positions) == 1
        assert positions[0]['name'] == 'BARØY'
        assert positions[0]['lat'] == 69.123
        assert positions[0]['lon'] == 16.456

def test_fetch_ferry_positions_api_failure():
    """Test graceful handling of API failures"""
    ferry_csv_data = [{'name': 'BARØY', 'imo': '9607394', 'mmsi': '257741000'}]

    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.RequestException("Network error")

        from ferry_api import fetch_ferry_positions
        positions = fetch_ferry_positions(ferry_csv_data, 'test_token')

        assert positions == []  # Empty list on failure
