def test_validate_mmsi():
    from scripts.process_ferries import validate_mmsi
    assert validate_mmsi("257122880") == True
    assert validate_mmsi("123") == False
    assert validate_mmsi("") == False

def test_validate_norwegian_waters():
    from scripts.process_ferries import validate_norwegian_waters
    assert validate_norwegian_waters(59.0, 10.0) == True  # Oslo
    assert validate_norwegian_waters(45.0, 10.0) == False  # Too south
    assert validate_norwegian_waters(85.0, 10.0) == False  # Too north

def test_process_ferry_csv(tmp_path):
    from scripts.process_ferries import process_ferry_csv

    # Create test CSV
    test_csv = tmp_path / "test_ferries.csv"
    test_csv.write_text("Navn,IMO-nummer,MMSI-nummer\nTest Ferry,123,257122880\n")

    ferries = process_ferry_csv(str(test_csv))
    assert len(ferries) == 1
    assert ferries[0]['name'] == 'Test Ferry'
    assert ferries[0]['mmsi'] == '257122880'

def test_get_api_headers():
    import os
    from scripts.process_ferries import get_api_headers

    # Test with missing token
    os.environ.pop('BARENTSWATCH_API_TOKEN', None)

    try:
        get_api_headers()
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "BARENTSWATCH_API_TOKEN" in str(e)

def test_get_single_ferry_position():
    from scripts.process_ferries import get_single_ferry_position
    import os
    from unittest.mock import patch

    # Mock response test
    class MockResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json_data = json_data

        def json(self):
            return self._json_data

    # Test with mock data and environment variable
    with patch.dict(os.environ, {'BARENTSWATCH_API_TOKEN': 'test-token'}), \
         patch('scripts.process_ferries.requests.get') as mock_get:

        mock_get.return_value = MockResponse(200, {
            'latitude': 59.0,
            'longitude': 10.0,
            'timestamp': '2026-03-25T10:00:00Z'
        })

        result = get_single_ferry_position("257122880")
        assert result == {'latitude': 59.0, 'longitude': 10.0, 'timestamp': '2026-03-25T10:00:00Z'}

def test_validate_timestamp():
    from scripts.process_ferries import validate_timestamp
    from datetime import datetime, timezone, timedelta

    # Recent timestamp (should be valid)
    recent = datetime.now(timezone.utc).isoformat()
    assert validate_timestamp(recent, 24) == True

    # Old timestamp (should be invalid)
    old = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    assert validate_timestamp(old, 24) == False

def test_process_ferry_position():
    from scripts.process_ferries import process_ferry_position

    api_data = {
        'latitude': 59.0,
        'longitude': 10.0,
        'timestamp': '2026-03-25T10:00:00Z'
    }

    result = process_ferry_position("257122880", api_data)
    assert result['lat'] == 59.0
    assert result['lon'] == 10.0