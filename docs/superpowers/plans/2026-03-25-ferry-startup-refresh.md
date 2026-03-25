# Ferry Startup Position Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically refresh Norwegian ferry positions from Barentswatch API during Flask app startup

**Architecture:** Extract ferry processing logic from external script into dedicated module, integrate OAuth2 token management, and call during app startup with graceful error handling

**Tech Stack:** Flask, requests, python-dotenv, Barentswatch AIS API, OAuth2

---

### Task 1: Environment Configuration Setup

**Files:**
- Create: `.env` (local only, not committed)
- Modify: `app.py:15`
- Modify: `tests/test_ferry_api.py`

- [ ] **Step 1: Write test for environment variable loading**

```python
# Add to tests/test_ferry_api.py (replacing existing file)
import os
import pytest
from unittest.mock import patch

def test_environment_variables_required():
    """Test that missing client credentials raise appropriate errors"""
    with patch.dict(os.environ, {}, clear=True):
        from ferry_api import get_barentswatch_token
        with pytest.raises(ValueError, match="BARENTSWATCH_CLIENT_ID"):
            get_barentswatch_token()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ferry_api.py::test_environment_variables_required -v`
Expected: FAIL with "No module named 'ferry_api'"

- [ ] **Step 3: Create environment file (local development only)**

```bash
# Create .env file (NOT committed to git)
echo "BARENTSWATCH_CLIENT_ID=PLACEHOLDER_REPLACE_WITH_REAL_ID" > .env
echo "BARENTSWATCH_CLIENT_SECRET=PLACEHOLDER_REPLACE_WITH_REAL_SECRET" >> .env
```

- [ ] **Step 4: Add dotenv import to app.py**

```python
# Add after line 14 (after existing imports)
from dotenv import load_dotenv

# Add after line 19 (before BASE_DIR assignment)
load_dotenv()
```

- [ ] **Step 5: Run environment test to verify still fails correctly**

Run: `python -m pytest tests/test_ferry_api.py::test_environment_variables_required -v`
Expected: Still FAIL with "No module named 'ferry_api'" (environment setup working, need to create module)

- [ ] **Step 6: Commit environment setup (excluding .env)**

```bash
git add app.py tests/test_ferry_api.py
git commit -m "feat: add environment configuration for Barentswatch API"
```

### Task 2: OAuth2 Token Management Module

**Files:**
- Create: `ferry_api.py`
- Modify: `test_ferry_api.py`

- [ ] **Step 1: Write failing test for token generation**

```python
# Add to test_ferry_api.py
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

def test_get_barentswatch_token_missing_credentials():
    """Test error handling for missing credentials"""
    with patch.dict(os.environ, {}, clear=True):
        from ferry_api import get_barentswatch_token
        with pytest.raises(ValueError, match="BARENTSWATCH_CLIENT_ID"):
            get_barentswatch_token()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ferry_api.py::test_get_barentswatch_token_success -v`
Expected: FAIL with "No module named 'ferry_api'"

- [ ] **Step 3: Create minimal ferry_api module**

```python
# Create ferry_api.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ferry_api.py -v`
Expected: PASS for both tests

- [ ] **Step 5: Commit OAuth2 token module**

```bash
git add ferry_api.py test_ferry_api.py
git commit -m "feat: add OAuth2 token management for Barentswatch API"
```

### Task 3: Ferry Position Fetching Logic

**Files:**
- Modify: `ferry_api.py:20-50`
- Modify: `test_ferry_api.py`

- [ ] **Step 1: Write failing test for ferry position fetching**

```python
# Add to test_ferry_api.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ferry_api.py::test_fetch_ferry_positions_success -v`
Expected: FAIL with "ImportError: cannot import name 'fetch_ferry_positions'"

- [ ] **Step 3: Implement ferry position fetching logic**

```python
# Add to ferry_api.py
from datetime import datetime, timezone

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
```

- [ ] **Step 4: Add missing imports**

```python
# Add to top of ferry_api.py
import sys
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_ferry_api.py -v`
Expected: PASS for all tests

- [ ] **Step 6: Commit ferry position fetching**

```bash
git add ferry_api.py test_ferry_api.py
git commit -m "feat: add ferry position fetching from Barentswatch API"
```

### Task 4: Ferry CSV Processing Integration

**Files:**
- Modify: `ferry_api.py:60-80`
- Modify: `test_ferry_api.py`

- [ ] **Step 1: Write test for CSV processing integration**

```python
# Add to test_ferry_api.py
from pathlib import Path

def test_load_ferry_data_from_csv():
    """Test loading and processing ferry data from CSV"""
    # Create temporary CSV content
    csv_content = """Navn,IMO-nummer,MMSI-nummer
BARØY,9607394,257741000
BASTØ ELECTRIC,9878993,257122880
TEST_FERRY,,999999999
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ferry_api.py::test_load_ferry_data_from_csv -v`
Expected: FAIL with "ImportError: cannot import name 'load_ferry_data_from_csv'"

- [ ] **Step 3: Implement CSV processing function**

```python
# Add to ferry_api.py
import csv
from pathlib import Path

def validate_mmsi(mmsi_str: str) -> bool:
    """Validate 9-digit MMSI format"""
    if not mmsi_str or mmsi_str.strip() == '':
        return False
    try:
        mmsi = int(mmsi_str)
        return 100000000 <= mmsi <= 999999999
    except ValueError:
        return False

def load_ferry_data_from_csv(csv_path: Path) -> list:
    """Load and validate ferry data from CSV file"""
    ferries = []

    if not csv_path.exists():
        print(f"[ADVARSEL] Ferry CSV not found: {csv_path}", file=sys.stderr)
        return []

    try:
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
    except Exception as e:
        print(f"[ADVARSEL] Error reading ferry CSV: {e}", file=sys.stderr)
        return []

    return ferries
```

- [ ] **Step 4: Add missing test import**

```python
# Add to test imports in test_ferry_api.py
from unittest.mock import mock_open
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_ferry_api.py::test_load_ferry_data_from_csv -v`
Expected: PASS

- [ ] **Step 6: Commit CSV processing integration**

```bash
git add ferry_api.py test_ferry_api.py
git commit -m "feat: add ferry CSV processing and validation"
```

### Task 5: Complete Ferry Refresh Function

**Files:**
- Modify: `ferry_api.py:90-110`
- Modify: `test_ferry_api.py`

- [ ] **Step 1: Write test for complete ferry refresh workflow**

```python
# Add to test_ferry_api.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ferry_api.py::test_refresh_ferry_positions_complete_workflow -v`
Expected: FAIL with "ImportError: cannot import name 'refresh_ferry_positions'"

- [ ] **Step 3: Implement complete refresh function**

```python
# Add to ferry_api.py
def refresh_ferry_positions(ferry_csv_path: Path) -> list:
    """Complete ferry position refresh workflow

    Args:
        ferry_csv_path: Path to CSV file containing ferry data

    Returns:
        List of ferry positions with current coordinates
    """
    try:
        # Load ferry data from CSV
        ferries = load_ferry_data_from_csv(ferry_csv_path)
        if not ferries:
            return []

        # Get fresh API token
        bearer_token = get_barentswatch_token()

        # Fetch current positions
        positions = fetch_ferry_positions(ferries, bearer_token)

        print(f"Ferry position refresh: {len(positions)} ferries with current positions", file=sys.stderr)
        return positions

    except Exception as e:
        print(f"[ADVARSEL] Ferry position refresh failed: {e}", file=sys.stderr)
        return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ferry_api.py -v`
Expected: PASS for all tests

- [ ] **Step 5: Commit complete ferry refresh function**

```bash
git add ferry_api.py test_ferry_api.py
git commit -m "feat: add complete ferry position refresh workflow"
```

### Task 6: App Startup Integration

**Files:**
- Modify: `app.py:71-82`
- Create: `tests/test_app_integration.py`

- [ ] **Step 1: Write test for app startup integration**

```python
# Create tests/test_app_integration.py
import pytest
import sys
from unittest.mock import patch, Mock
from pathlib import Path

def test_ferry_refresh_called_during_startup():
    """Test that ferry refresh is called during app startup"""
    mock_positions = [
        {'name': 'BARØY', 'mmsi': '257741000', 'lat': 69.123, 'lon': 16.456}
    ]

    with patch('ferry_api.refresh_ferry_positions', return_value=mock_positions) as mock_refresh:
        # Import app module to test startup behavior
        import app

        # Clear any existing ferry data
        app._ferries = []

        # Run startup
        app.startup()

        # Verify refresh was called
        mock_refresh.assert_called_once()
        assert len(app._ferries) == 1
        assert app._ferries[0]['name'] == 'BARØY'

def test_ferry_loading_failure_graceful():
    """Test graceful handling of ferry loading failure"""
    with patch('ferry_api.refresh_ferry_positions', return_value=[]):
        import app

        app._ferries = []
        app.startup()

        # Should continue with empty ferry list, no startup error
        assert app._ferries == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest test_app_integration.py -v`
Expected: FAIL due to missing ferry integration in app.py

- [ ] **Step 3: Add ferry_api import to app.py**

```python
# Add to imports section around line 14
from ferry_api import refresh_ferry_positions
```

- [ ] **Step 4: Replace ferry loading section in startup()**

```python
# Replace lines 71-82 in startup() function:
    # --- Ferries (Fresh API Data) ---
    try:
        ferries_csv_path = BASE_DIR / "data" / "ferries.csv"
        _ferries = refresh_ferry_positions(ferries_csv_path)
        print(f"Lastet {len(_ferries)} ferjer fra Barentswatch API", file=sys.stderr)
    except Exception as e:
        print(f"[ADVARSEL] Ferry API refresh failed: {e}", file=sys.stderr)
        _ferries = []

# This replaces the existing ferry section:
# Lines 71-82 currently contain static JSON loading that should be replaced
```

- [ ] **Step 5: Run integration test to verify it passes**

Run: `python -m pytest tests/test_app_integration.py -v`
Expected: PASS (may need to adjust test based on actual startup behavior)

- [ ] **Step 6: Test app startup manually**

Run: `python app.py`
Expected: App starts successfully with message "Lastet X ferjer fra Barentswatch API"

- [ ] **Step 7: Commit app integration**

```bash
git add app.py test_app_integration.py
git commit -m "feat: integrate ferry position refresh into app startup"
```

### Task 7: Production Environment Setup

**Files:**
- Create: `docs/DEPLOYMENT.md`
- Modify: `README.md` (if exists)

- [ ] **Step 1: Document environment variable setup**

```markdown
# Create docs/DEPLOYMENT.md
# Ferry Position API Configuration

## Local Development

1. Create `.env` file:
```bash
BARENTSWATCH_CLIENT_ID=your_client_id_here
BARENTSWATCH_CLIENT_SECRET=your_client_secret_here
```

2. Install dependencies:
```bash
pip install python-dotenv requests
```

## Railway Production Deployment

### Environment Variables Setup

1. **Railway Dashboard:**
   - Go to your project → Variables tab
   - Add these environment variables:

```
BARENTSWATCH_CLIENT_ID=your_actual_client_id_here
BARENTSWATCH_CLIENT_SECRET=your_actual_client_secret_here
```

2. **Security Notes:**
   - ✅ Secrets stored in Railway dashboard (secure)
   - ✅ Local .env not committed to git
   - ✅ No hardcoded credentials in code

### Testing Configuration

Test locally:
```bash
python -c "from ferry_api import get_barentswatch_token; print('Token:', get_barentswatch_token()[:50] + '...')"
```

Expected: `Token: eyJhbGciOiJSUzI1NiIs...`

## Troubleshooting

- **401 Unauthorized**: Check client credentials
- **Network errors**: Check internet connection / API availability
- **Empty ferry list**: Normal if API has no fresh position data
```

- [ ] **Step 2: Create production checklist**

```markdown
# Add to docs/DEPLOYMENT.md

## Production Deployment Checklist

- [ ] Railway environment variables set
- [ ] App starts without errors
- [ ] Ferry API endpoint returns data: `curl https://your-app.railway.app/api/ferries`
- [ ] Check logs for "Lastet X ferjer fra Barentswatch API"
- [ ] Verify ferries appear on map

## Monitoring

Check ferry data refresh:
- App logs show successful ferry loading on startup
- `/api/ferries` endpoint returns current positions
- Ferry markers visible on map interface
```

- [ ] **Step 3: Update main documentation**

```markdown
# Add to README.md (or create if doesn't exist)

## Ferry Position Data

The app automatically fetches live Norwegian ferry positions from the Barentswatch AIS API during startup.

**API Source:** [Barentswatch AIS API](https://developer.barentswatch.no/docs/AIS/)
**Refresh:** Positions updated each time the app starts
**Coverage:** 90+ Norwegian coastal ferries

### Configuration

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for environment setup.
```

- [ ] **Step 4: Commit documentation**

```bash
git add docs/DEPLOYMENT.md README.md
git commit -m "docs: add ferry API configuration and deployment guide"
```

### Task 8: Final Integration Testing

**Files:**
- Test: Manual verification

- [ ] **Step 1: Run complete test suite**

Run: `python -m pytest tests/test_ferry_api.py tests/test_app_integration.py -v`
Expected: All tests PASS

- [ ] **Step 2: Test app startup with real API**

Run: `python app.py`
Expected:
- App starts successfully
- Message: "Lastet X ferjer fra Barentswatch API"
- No error messages related to ferries

- [ ] **Step 3: Test ferry API endpoint**

Run: `curl http://localhost:5000/api/ferries | python -m json.tool | head -20`
Expected: JSON array with ferry position data

- [ ] **Step 4: Test web interface**

1. Open: `http://localhost:5000`
2. Search for: "Bastø" or "Landegode"
3. Expected: Ferry appears in search results with live position

- [ ] **Step 5: Test error handling**

```bash
# Test with invalid credentials
mv .env .env.backup
python app.py
```
Expected: App starts with empty ferry list, no crashes

```bash
# Restore credentials
mv .env.backup .env
```

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat: complete ferry position auto-refresh implementation

- Automatic ferry position refresh during app startup
- OAuth2 token management for Barentswatch API
- CSV processing with MMSI validation
- Norwegian waters coordinate validation
- Graceful error handling with empty ferry list fallback
- Production-ready environment variable configuration
- Comprehensive test coverage"
```

---

## Summary

This plan implements automatic ferry position refresh by:

1. **Environment Setup** - Secure credential management
2. **OAuth2 Integration** - Automatic bearer token generation
3. **API Client** - Ferry position fetching from Barentswatch
4. **CSV Processing** - Ferry data validation and loading
5. **App Integration** - Seamless startup integration
6. **Production Ready** - Railway deployment configuration
7. **Testing** - Comprehensive test coverage
8. **Documentation** - Deployment and configuration guides

The implementation maintains the existing app architecture while replacing static ferry data with live API integration.