import pytest
import json
import os
import sys
import time
import subprocess
from pathlib import Path

# Ensure the app module can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# BASIC DATA VALIDATION TESTS
# =============================================================================

def test_shipyards_json_exists():
    """Test that shipyards.json file exists after processing"""
    shipyards_path = Path("data/shipyards.json")
    assert shipyards_path.exists(), "shipyards.json should exist after CSV processing"


def test_shipyards_json_structure():
    """Test that shipyards.json has correct structure"""
    with open("data/shipyards.json", 'r', encoding='utf-8') as f:
        shipyards = json.load(f)

    assert isinstance(shipyards, list), "Shipyards should be a list"
    assert len(shipyards) > 5, "Should have multiple shipyards after processing"

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


def test_data_quality_validation():
    """Validate quality of processed shipyard data"""
    with open("data/shipyards.json") as f:
        shipyards = json.load(f)

    for shipyard in shipyards:
        # Validate coordinates are in Norway
        lat, lon = shipyard['lat'], shipyard['lon']
        assert 58 <= lat <= 72, f"Latitude {lat} should be in Norway range (58-72)"
        assert 4 <= lon <= 32, f"Longitude {lon} should be in Norway range (4-32)"

        # Validate required fields exist and are non-empty
        assert shipyard['name'], "Name should not be empty"
        assert shipyard['city'], "City should not be empty"
        assert shipyard['address'], "Address should not be empty"
        assert shipyard['facilities']['postalCode'], "Postal code required"


# =============================================================================
# GEOCODING SCRIPT TESTS
# =============================================================================

def test_geocoding_script_exists():
    """Test that geocoding script exists"""
    script_path = Path("scripts/geocode_shipyards.py")
    assert script_path.exists(), "Geocoding script should exist"


def test_geocoding_script_executable():
    """Test that geocoding script is executable"""
    script_path = Path("scripts/geocode_shipyards.py")
    assert os.access(script_path, os.X_OK), "Geocoding script should be executable"


def test_end_to_end_shipyard_workflow():
    """Test complete shipyard workflow from CSV to frontend"""
    # Check if source CSV exists, skip if not available
    csv_path = Path(__file__).parent.parent / "Verftoversikt-Oversikt Verksted(1).csv"
    if not csv_path.exists():
        pytest.skip("Source shipyard CSV file not available in this environment")

    # Verify geocoding script runs successfully
    result = subprocess.run(
        ['python3', 'scripts/geocode_shipyards.py'],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 0, f"Geocoding script failed: {result.stderr}"

    # Verify JSON file creation and validity
    shipyards_path = Path("data/shipyards.json")
    assert shipyards_path.exists(), "shipyards.json should be created by geocoding script"

    with open(shipyards_path) as f:
        shipyards = json.load(f)
    assert len(shipyards) > 5, "Should have multiple shipyards after processing"

    # Verify all shipyards have valid structure
    for shipyard in shipyards:
        assert 'name' in shipyard and shipyard['name'], "Each shipyard needs a name"
        assert 'lat' in shipyard and isinstance(shipyard['lat'], (int, float))
        assert 'lon' in shipyard and isinstance(shipyard['lon'], (int, float))
        assert 'facilities' in shipyard and isinstance(shipyard['facilities'], dict)


# =============================================================================
# API ENDPOINT TESTS
# =============================================================================

def test_shipyard_api_endpoint():
    """Test that /api/shipyards endpoint returns shipyard data"""
    try:
        from app import app, startup

        startup()  # Ensure app is initialized
        app.config['TESTING'] = True
        client = app.test_client()

        response = client.get('/api/shipyards')

        assert response.status_code == 200, f"API should return 200, got {response.status_code}"
        data = response.get_json()
        assert isinstance(data, list), "API should return a list"
        assert len(data) > 5, "API should return multiple shipyards"

        # Verify each item has required fields
        for shipyard in data:
            assert 'name' in shipyard, "Shipyard should have name"
            assert 'lat' in shipyard, "Shipyard should have lat"
            assert 'lon' in shipyard, "Shipyard should have lon"
            assert 'city' in shipyard, "Shipyard should have city"

    except ImportError:
        pytest.skip("App not available for API testing")


def test_api_shipyards_matches_json():
    """Test that API endpoint data matches JSON file"""
    try:
        from app import app, startup

        startup()  # Ensure app is initialized

        # Load JSON file
        with open("data/shipyards.json") as f:
            json_shipyards = json.load(f)

        # Get from API
        app.config['TESTING'] = True
        client = app.test_client()
        response = client.get('/api/shipyards')

        assert response.status_code == 200
        api_shipyards = response.get_json()

        # Should have same count
        assert len(api_shipyards) == len(json_shipyards), \
            "API and JSON should have same shipyard count"

        # Verify specific shipyards exist in both
        json_names = {s['name'] for s in json_shipyards}
        api_names = {s['name'] for s in api_shipyards}
        assert json_names == api_names, "API and JSON should have same shipyard names"

    except ImportError:
        pytest.skip("App not available for API testing")


def test_api_status_endpoint():
    """Test that /api/status endpoint is available"""
    try:
        from app import app, startup

        startup()  # Ensure app is initialized
        app.config['TESTING'] = True
        client = app.test_client()

        response = client.get('/api/status')
        assert response.status_code in [200, 503], "Status endpoint should be available"

        if response.status_code == 200:
            data = response.get_json()
            assert 'ok' in data, "Status should have 'ok' field"

    except ImportError:
        pytest.skip("App not available for API testing")


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

def test_shipyard_search_performance():
    """Test that shipyard search performs adequately"""
    # Load shipyards
    with open("data/shipyards.json") as f:
        shipyards = json.load(f)

    # Simulate frontend search - find shipyards with common terms
    # Use a term that actually exists in the data
    start_time = time.time()
    matches = [s for s in shipyards if 'verft' in s['name'].lower() or 'yard' in s['name'].lower()]
    search_time = (time.time() - start_time) * 1000  # Convert to ms

    assert search_time < 100, f"Search should be fast (<100ms), took {search_time:.2f}ms"
    assert len(matches) > 0, "Should find shipyards with common terms"


def test_all_shipyards_search():
    """Test search across all shipyards for common terms"""
    with open("data/shipyards.json") as f:
        shipyards = json.load(f)

    # Test searching for common terms
    search_terms = ['verft', 'yard', 'as', 'vik']
    total_time = 0

    for term in search_terms:
        start_time = time.time()
        matches = [s for s in shipyards if term in s['name'].lower()]
        elapsed = (time.time() - start_time) * 1000
        total_time += elapsed

        assert elapsed < 100, f"Search for '{term}' took {elapsed:.2f}ms"

    avg_time = total_time / len(search_terms)
    assert avg_time < 50, f"Average search time should be <50ms, was {avg_time:.2f}ms"


def test_json_load_performance():
    """Test that JSON file loads quickly"""
    start_time = time.time()
    with open("data/shipyards.json") as f:
        shipyards = json.load(f)
    load_time = (time.time() - start_time) * 1000

    assert load_time < 100, f"JSON load should be fast (<100ms), took {load_time:.2f}ms"
    assert len(shipyards) > 0, "JSON should contain shipyards"


# =============================================================================
# DATA INTEGRITY TESTS
# =============================================================================

def test_no_duplicate_shipyards():
    """Test that there are no duplicate shipyards"""
    with open("data/shipyards.json") as f:
        shipyards = json.load(f)

    names = [s['name'] for s in shipyards]
    assert len(names) == len(set(names)), "There should be no duplicate shipyard names"


def test_shipyard_coordinates_valid():
    """Test that all shipyard coordinates are valid and in Norway"""
    with open("data/shipyards.json") as f:
        shipyards = json.load(f)

    for shipyard in shipyards:
        lat = shipyard['lat']
        lon = shipyard['lon']

        # Check type
        assert isinstance(lat, (int, float)), f"{shipyard['name']}: lat should be numeric"
        assert isinstance(lon, (int, float)), f"{shipyard['name']}: lon should be numeric"

        # Check range (Norway bounds)
        assert 57 <= lat <= 71, \
            f"{shipyard['name']}: latitude {lat} outside Norway range"
        assert 3 <= lon <= 32, \
            f"{shipyard['name']}: longitude {lon} outside Norway range"

        # Check not obviously wrong (0,0)
        assert not (lat == 0 and lon == 0), \
            f"{shipyard['name']}: coordinates are (0,0), likely geocoding failure"


def test_shipyard_cities_valid():
    """Test that all shipyards have valid city information"""
    with open("data/shipyards.json") as f:
        shipyards = json.load(f)

    for shipyard in shipyards:
        assert shipyard['city'], f"{shipyard['name']}: city should not be empty"
        assert isinstance(shipyard['city'], str), \
            f"{shipyard['name']}: city should be a string"
        assert len(shipyard['city']) > 1, \
            f"{shipyard['name']}: city '{shipyard['city']}' seems too short"


def test_shipyard_facilities_format():
    """Test that facilities are properly formatted"""
    with open("data/shipyards.json") as f:
        shipyards = json.load(f)

    for shipyard in shipyards:
        facilities = shipyard.get('facilities', {})
        assert isinstance(facilities, dict), \
            f"{shipyard['name']}: facilities should be a dict"

        # Check for common expected keys
        expected_keys = ['postalCode', 'homepage']
        for key in expected_keys:
            assert key in facilities, \
                f"{shipyard['name']}: facilities missing '{key}'"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

def test_csv_source_file_exists():
    """Test that the source CSV file exists"""
    # Check specifically for the shipyard CSV file
    csv_path = Path("Verftoversikt-Oversikt Verksted(1).csv")
    if not csv_path.exists():
        pytest.skip("Source shipyard CSV file not available in this environment")

    csv_files = list(Path(".").glob("*.csv"))
    assert len(csv_files) > 0, "Should have at least one CSV file (source data)"


def test_full_pipeline_integration():
    """Test the complete pipeline: CSV → geocoding → JSON → API"""
    # Check if source CSV exists, skip if not available
    csv_path = Path("Verftoversikt-Oversikt Verksted(1).csv")
    if not csv_path.exists():
        pytest.skip("Source shipyard CSV file not available for full pipeline test")

    try:
        from app import app, startup

        # Initialize app
        startup()

        # 1. Check CSV file exists
        csv_files = list(Path(".").glob("*.csv"))
        assert len(csv_files) > 0, "Source CSV should exist"

        # 2. Check JSON file is created
        json_path = Path("data/shipyards.json")
        assert json_path.exists(), "shipyards.json should be created"

        # 3. Verify JSON structure
        with open(json_path) as f:
            shipyards = json.load(f)
        assert len(shipyards) > 5, "Should have processed multiple shipyards"

        # 4. Verify API can serve the data
        app.config['TESTING'] = True
        client = app.test_client()
        response = client.get('/api/shipyards')
        assert response.status_code == 200, "API should be accessible"

        api_data = response.get_json()
        assert len(api_data) == len(shipyards), "API should return same data as JSON"

        print(f"\n✅ Full pipeline integration test passed:")
        print(f"   - CSV file found: {csv_files[0].name}")
        print(f"   - Shipyards processed: {len(shipyards)}")
        print(f"   - API endpoint: /api/shipyards")

    except ImportError:
        pytest.skip("App not available for full integration test")
