import os
import sys
import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
import requests
import csv

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

def test_fetch_ferry_positions_norwegian_waters_validation():
    """Test that ferries outside Norwegian waters are filtered out"""
    mock_vessels = [
        {
            'mmsi': 257741000,
            'latitude': 69.123,  # Valid Norwegian waters
            'longitude': 16.456,
            'timestamp': '2026-03-25T10:30:00Z'
        },
        {
            'mmsi': 257741001,
            'latitude': 50.0,  # Too far south
            'longitude': 5.0,
            'timestamp': '2026-03-25T10:30:00Z'
        },
        {
            'mmsi': 257741002,
            'latitude': 85.0,  # Too far north
            'longitude': 20.0,
            'timestamp': '2026-03-25T10:30:00Z'
        },
        {
            'mmsi': 257741003,
            'latitude': 65.0,
            'longitude': 2.0,  # Too far west
            'timestamp': '2026-03-25T10:30:00Z'
        },
        {
            'mmsi': 257741004,
            'latitude': 65.0,
            'longitude': 35.0,  # Too far east
            'timestamp': '2026-03-25T10:30:00Z'
        }
    ]

    ferry_csv_data = [
        {'name': 'BARØY', 'imo': '9607394', 'mmsi': '257741000'},
        {'name': 'FERRY2', 'imo': '9607395', 'mmsi': '257741001'},
        {'name': 'FERRY3', 'imo': '9607396', 'mmsi': '257741002'},
        {'name': 'FERRY4', 'imo': '9607397', 'mmsi': '257741003'},
        {'name': 'FERRY5', 'imo': '9607398', 'mmsi': '257741004'},
    ]

    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_vessels
        mock_get.return_value = mock_response

        from ferry_api import fetch_ferry_positions
        positions = fetch_ferry_positions(ferry_csv_data, 'test_token')

        # Only the first ferry should be included (within 58-81°N, 4-32°E)
        assert len(positions) == 1
        assert positions[0]['name'] == 'BARØY'

def test_fetch_ferry_positions_missing_coordinates():
    """Test that ferries with missing coordinates are skipped"""
    mock_vessels = [
        {
            'mmsi': 257741000,
            'latitude': 69.123,
            'longitude': 16.456,
            'timestamp': '2026-03-25T10:30:00Z'
        },
        {
            'mmsi': 257741001,
            'latitude': None,  # Missing latitude
            'longitude': 16.456,
            'timestamp': '2026-03-25T10:30:00Z'
        },
        {
            'mmsi': 257741002,
            'latitude': 69.123,
            'longitude': None,  # Missing longitude
            'timestamp': '2026-03-25T10:30:00Z'
        },
        {
            'mmsi': 257741003,
            # Both latitude and longitude missing
            'timestamp': '2026-03-25T10:30:00Z'
        }
    ]

    ferry_csv_data = [
        {'name': 'BARØY', 'imo': '9607394', 'mmsi': '257741000'},
        {'name': 'FERRY2', 'imo': '9607395', 'mmsi': '257741001'},
        {'name': 'FERRY3', 'imo': '9607396', 'mmsi': '257741002'},
        {'name': 'FERRY4', 'imo': '9607397', 'mmsi': '257741003'},
    ]

    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_vessels
        mock_get.return_value = mock_response

        from ferry_api import fetch_ferry_positions
        positions = fetch_ferry_positions(ferry_csv_data, 'test_token')

        # Only the first ferry should be included (has both coordinates)
        assert len(positions) == 1
        assert positions[0]['name'] == 'BARØY'

def test_fetch_ferry_positions_http_errors():
    """Test handling of various HTTP error codes"""
    ferry_csv_data = [{'name': 'BARØY', 'imo': '9607394', 'mmsi': '257741000'}]

    for status_code in [400, 401, 403, 404, 500, 502, 503]:
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = status_code
            mock_get.return_value = mock_response

            from ferry_api import fetch_ferry_positions
            positions = fetch_ferry_positions(ferry_csv_data, 'test_token')

            assert positions == [], f"Expected empty list for HTTP {status_code}"

def test_fetch_ferry_positions_malformed_json():
    """Test handling of malformed JSON response"""
    ferry_csv_data = [{'name': 'BARØY', 'imo': '9607394', 'mmsi': '257741000'}]

    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        from ferry_api import fetch_ferry_positions
        positions = fetch_ferry_positions(ferry_csv_data, 'test_token')

        # Should return empty list, not raise an exception
        assert positions == []

def test_fetch_ferry_positions_mmsi_type_consistency():
    """Test that both integer and string MMSI values are handled correctly"""
    mock_vessels = [
        {
            'mmsi': 257741000,  # Integer MMSI
            'latitude': 69.123,
            'longitude': 16.456,
            'timestamp': '2026-03-25T10:30:00Z'
        },
        {
            'mmsi': '257741001',  # String MMSI
            'latitude': 69.456,
            'longitude': 16.789,
            'timestamp': '2026-03-25T10:30:00Z'
        }
    ]

    ferry_csv_data = [
        {'name': 'BARØY', 'imo': '9607394', 'mmsi': 257741000},  # Integer in list
        {'name': 'FERRY2', 'imo': '9607395', 'mmsi': '257741001'},  # String in list
    ]

    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_vessels
        mock_get.return_value = mock_response

        from ferry_api import fetch_ferry_positions
        positions = fetch_ferry_positions(ferry_csv_data, 'test_token')

        # Both ferries should be found despite MMSI type differences
        assert len(positions) == 2
        assert positions[0]['name'] == 'BARØY'
        assert positions[1]['name'] == 'FERRY2'
        # All MMSI values in output should be strings
        assert positions[0]['mmsi'] == '257741000'
        assert positions[1]['mmsi'] == '257741001'

def test_validate_norwegian_waters():
    """Test Norwegian waters boundary validation"""
    from ferry_api import validate_norwegian_waters

    # Valid coordinates within Norwegian waters
    assert validate_norwegian_waters(60.0, 5.0) is True
    assert validate_norwegian_waters(69.5, 16.5) is True
    assert validate_norwegian_waters(81.0, 32.0) is True
    assert validate_norwegian_waters(58.0, 4.0) is True

    # Invalid coordinates outside Norwegian waters
    assert validate_norwegian_waters(57.9, 5.0) is False  # Too south
    assert validate_norwegian_waters(81.1, 5.0) is False  # Too north
    assert validate_norwegian_waters(60.0, 3.9) is False  # Too west
    assert validate_norwegian_waters(60.0, 32.1) is False  # Too east

def test_load_ferry_data_from_csv():
    """Test loading and processing ferry data from CSV"""
    # Create temporary CSV content
    csv_content = """Navn,IMO-nummer,MMSI-nummer
BARØY,9607394,257741000
BASTØ ELECTRIC,9878993,257122880
TEST_FERRY,,999999999999
INVALID_FERRY,,invalid_mmsi
"""

    with patch('pathlib.Path.exists', return_value=True):
        with patch('builtins.open', mock_open(read_data=csv_content)):
            from ferry_api import load_ferry_data_from_csv
            ferries = load_ferry_data_from_csv(Path("test.csv"))

            # Should only include ferries with valid MMSI
            assert len(ferries) == 2
            assert ferries[0]['name'] == 'BARØY'
            assert ferries[0]['mmsi'] == '257741000'
            assert ferries[1]['name'] == 'BASTØ ELECTRIC'
            assert ferries[1]['mmsi'] == '257122880'

def test_load_ferry_data_from_csv_encoding_error():
    """Test handling of CSV encoding errors"""
    with patch('pathlib.Path.exists', return_value=True):
        with patch('builtins.open', side_effect=UnicodeDecodeError(
            'utf-8', b'', 0, 1, 'invalid start byte'
        )):
            from ferry_api import load_ferry_data_from_csv
            ferries = load_ferry_data_from_csv(Path("test.csv"))

            # Should return empty list, not raise an exception
            assert ferries == []

def test_load_ferry_data_from_csv_missing_columns():
    """Test handling of CSV with missing required columns"""
    # CSV missing MMSI-nummer column
    csv_content = """Navn,IMO-nummer
BARØY,9607394
BASTØ ELECTRIC,9878993
"""

    with patch('pathlib.Path.exists', return_value=True):
        with patch('builtins.open', mock_open(read_data=csv_content)):
            from ferry_api import load_ferry_data_from_csv
            ferries = load_ferry_data_from_csv(Path("test.csv"))

            # Should return empty list due to missing required column
            assert ferries == []

def test_load_ferry_data_from_csv_malformed_csv():
    """Test handling of malformed CSV structure"""
    # Create CSV with mismatched columns
    csv_content = """Navn,IMO-nummer,MMSI-nummer
BARØY,9607394
BASTØ ELECTRIC,9878993,257122880,extra_column
"""

    with patch('pathlib.Path.exists', return_value=True):
        with patch('builtins.open', mock_open(read_data=csv_content)):
            from ferry_api import load_ferry_data_from_csv
            ferries = load_ferry_data_from_csv(Path("test.csv"))

            # DictReader handles mismatched columns gracefully
            # Only BASTØ ELECTRIC has valid data (name + valid MMSI)
            assert len(ferries) == 1
            assert ferries[0]['name'] == 'BASTØ ELECTRIC'

def test_load_ferry_data_from_csv_file_not_found():
    """Test handling of missing CSV file"""
    with patch('pathlib.Path.exists', return_value=False):
        from ferry_api import load_ferry_data_from_csv
        ferries = load_ferry_data_from_csv(Path("nonexistent.csv"))

        # Should return empty list when file doesn't exist
        assert ferries == []

def test_load_ferry_data_from_csv_empty_file():
    """Test handling of empty CSV file"""
    csv_content = """Navn,IMO-nummer,MMSI-nummer
"""

    with patch('pathlib.Path.exists', return_value=True):
        with patch('builtins.open', mock_open(read_data=csv_content)):
            from ferry_api import load_ferry_data_from_csv
            ferries = load_ferry_data_from_csv(Path("test.csv"))

            # Should return empty list when no data rows
            assert ferries == []

def test_load_ferry_data_from_csv_whitespace_handling():
    """Test that whitespace is properly trimmed from fields"""
    csv_content = """Navn,IMO-nummer,MMSI-nummer
  BARØY  ,  9607394  ,  257741000
BASTØ ELECTRIC, 9878993 , 257122880
"""

    with patch('pathlib.Path.exists', return_value=True):
        with patch('builtins.open', mock_open(read_data=csv_content)):
            from ferry_api import load_ferry_data_from_csv
            ferries = load_ferry_data_from_csv(Path("test.csv"))

            # Whitespace should be trimmed
            assert len(ferries) == 2
            assert ferries[0]['name'] == 'BARØY'
            assert ferries[0]['imo'] == '9607394'
            assert ferries[0]['mmsi'] == '257741000'
            assert ferries[1]['name'] == 'BASTØ ELECTRIC'

def test_refresh_ferry_positions_complete_workflow():
    """Test complete ferry refresh from CSV to positions"""
    csv_content = "Navn,IMO-nummer,MMSI-nummer\nBARØY,9607394,257741000\n"
    api_vessels = [{
        'mmsi': 257741000,
        'latitude': 69.123,
        'longitude': 16.456,
        'timestamp': '2026-03-25T10:30:00Z'
    }]

    with patch('pathlib.Path.exists', return_value=True):
        with patch('builtins.open', mock_open(read_data=csv_content)):
            with patch('ferry_api.get_barentswatch_token', return_value='test_token'):
                with patch('requests.get') as mock_get:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = api_vessels
                    mock_get.return_value = mock_response

                    from ferry_api import refresh_ferry_positions
                    positions = refresh_ferry_positions(Path("test.csv"))

                    assert len(positions) == 1
                    assert positions[0]['name'] == 'BARØY'
                    assert positions[0]['lat'] == 69.123

def test_refresh_ferry_positions_handles_token_failure():
    """Test graceful handling when token generation fails"""
    with patch('ferry_api.get_barentswatch_token', side_effect=ValueError("Token failed")):
        from ferry_api import refresh_ferry_positions
        positions = refresh_ferry_positions(Path("test.csv"))
        assert positions == []
