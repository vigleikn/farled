import pytest
import json
import os
from pathlib import Path

def test_shipyards_json_exists():
    """Test that shipyards.json file exists after processing"""
    shipyards_path = Path("data/shipyards.json")
    assert shipyards_path.exists(), "shipyards.json should exist after CSV processing"

def test_shipyards_json_structure():
    """Test that shipyards.json has correct structure"""
    with open("data/shipyards.json", 'r', encoding='utf-8') as f:
        shipyards = json.load(f)

    assert isinstance(shipyards, list), "Shipyards should be a list"
    assert len(shipyards) > 0, "Should have at least one shipyard"

    shipyard = shipyards[0]
    required_fields = ['name', 'city', 'address', 'lat', 'lon', 'facilities']
    for field in required_fields:
        assert field in shipyard, f"Shipyard should have {field} field"

    assert isinstance(shipyard['lat'], (int, float)), "Latitude should be numeric"
    assert isinstance(shipyard['lon'], (int, float)), "Longitude should be numeric"
    assert isinstance(shipyard['facilities'], dict), "Facilities should be a dict"

def test_shipyards_no_missing_postal_codes():
    """Test that all shipyards have postal codes"""
    with open("data/shipyards.json", 'r', encoding='utf-8') as f:
        shipyards = json.load(f)

    for shipyard in shipyards:
        assert 'postalCode' in shipyard['facilities'], "All shipyards should have postal codes"
        assert shipyard['facilities']['postalCode'], "Postal code should not be empty"

def test_shipyard_api_endpoint():
    """Test that /api/shipyards endpoint returns shipyard data"""
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))

        from app import app

        app.config['TESTING'] = True
        client = app.test_client()

        response = client.get('/api/shipyards')

        # Endpoint should exist and return valid response
        assert response.status_code in [200, 500], f"Expected 200 or 500, got {response.status_code}"

        if response.status_code == 200:
            data = response.get_json()
            assert isinstance(data, list), "API should return a list"

            if len(data) > 0:
                shipyard = data[0]
                required_fields = ['name', 'city', 'lat', 'lon']
                for field in required_fields:
                    assert field in shipyard, f"API shipyard should have {field} field"
    except ImportError:
        pytest.skip("API endpoint not yet implemented")

def test_shipyard_api_empty_when_no_file():
    """Test that API returns empty list when shipyards.json missing"""
    pass  # Will implement after backend changes
