# Shipyard CSV Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add searchable Norwegian shipyard data from CSV to the sea route calculator dropdown system.

**Architecture:** Follows existing allQuays pattern - pre-process CSV to JSON with coordinates, load in backend, search in frontend dropdown between "Kaier" and "Steder" sections.

**Tech Stack:** Python CSV processing, Kartverket geocoding API, Flask backend, JavaScript frontend integration

---

### Task 1: CSV Data Processing Script

**Files:**
- Create: `scripts/geocode_shipyards.py`
- Test: `tests/test_shipyard_integration.py`
- Output: `data/shipyards.json`

- [ ] **Step 1: Create tests directory and write failing test for shipyard data structure**

```bash
mkdir -p tests
```

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_shipyard_integration.py::test_shipyards_json_exists -v`
Expected: FAIL with "shipyards.json should exist after CSV processing"

- [ ] **Step 3: Create scripts directory**

```bash
mkdir -p scripts
```

- [ ] **Step 4: Write CSV geocoding script**

```python
#!/usr/bin/env python3
"""
Geocoding script for Norwegian shipyards CSV.
Reads Verftoversikt CSV, geocodes addresses, outputs structured JSON.
"""

import csv
import json
import urllib.request
import urllib.parse
import time
from pathlib import Path

def geocode_address(address, postal_code, city):
    """Geocode Norwegian address using Kartverket API"""
    # Same API as used in main app
    search_text = f"{address}, {postal_code} {city}"
    url = (
        "https://ws.geonorge.no/adresser/v1/sok?"
        + urllib.parse.urlencode({"sok": search_text, "treffPerSide": "1", "utkoordsys": "4258"})
    )

    headers = {"User-Agent": "sjovei-kalkulator"}

    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, headers=headers), timeout=5
        ) as resp:
            data = json.loads(resp.read())

        adresser = data.get("adresser", [])
        if adresser:
            pt = adresser[0].get("representasjonspunkt", {})
            if pt.get("lat") and pt.get("lon"):
                return pt["lat"], pt["lon"]
    except Exception as e:
        print(f"Geocoding failed for {search_text}: {e}")

    return None, None

def format_facility_key(key):
    """Convert CSV column names to camelCase"""
    key_mapping = {
        "Postal code": "postalCode",
        "DocksDry": "docksDry",
        "TowingDockSlip": "towingDockSlip",
        "DocksWet": "docksWet",
        "Heated hall": "heatedHall"
    }
    return key_mapping.get(key, key.lower().replace(" ", ""))

def process_shipyards_csv():
    """Main function to process CSV and generate JSON"""
    # Use paths relative to script location
    BASE_DIR = Path(__file__).parent.parent  # Go up from scripts/ to project root
    csv_path = BASE_DIR / "Verftoversikt-Oversikt Verksted(1).csv"
    output_path = BASE_DIR / "data" / "shipyards.json"

    if not csv_path.exists():
        print(f"Error: {csv_path} not found")
        return False

    # Ensure data directory exists
    output_path.parent.mkdir(exist_ok=True)

    shipyards = []
    failed_geocoding = []

    with open(csv_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)

        for row_num, row in enumerate(reader, start=2):
            # Skip entries without postal codes
            postal_code = row.get("Postal code", "").strip()
            if not postal_code:
                print(f"Row {row_num}: Skipping {row.get('Verft', 'Unknown')} - no postal code")
                continue

            name = row.get("Verft", "").strip()
            address = row.get("Adress", "").strip()
            city = row.get("City", "").strip()

            if not all([name, address, city]):
                print(f"Row {row_num}: Skipping {name} - missing required fields")
                continue

            # Geocode the address
            print(f"Geocoding: {name} in {city}...")
            lat, lon = geocode_address(address, postal_code, city)

            if lat is None or lon is None:
                failed_geocoding.append(f"{name} - {address}, {postal_code} {city}")
                print(f"  ❌ Failed to geocode {name}")
                continue

            # Build facilities object
            facilities = {}
            for key, value in row.items():
                if key in ["Verft", "Adress", "City"]:
                    continue  # Skip main fields, they're handled separately

                formatted_key = format_facility_key(key)
                facilities[formatted_key] = value.strip() if value else ""

            shipyard = {
                "name": name,
                "city": city,
                "address": f"{address}, {postal_code} {city}",
                "lat": lat,
                "lon": lon,
                "facilities": facilities
            }

            shipyards.append(shipyard)
            print(f"  ✅ Success: {name} ({lat:.4f}, {lon:.4f})")

            # Rate limit to be nice to the API
            time.sleep(0.5)

    # Save results
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(shipyards, f, ensure_ascii=False, indent=2)

    print(f"\n📊 Processing complete:")
    print(f"  ✅ Successfully geocoded: {len(shipyards)} shipyards")
    print(f"  ❌ Failed geocoding: {len(failed_geocoding)} entries")
    print(f"  📁 Output saved to: {output_path}")

    if failed_geocoding:
        print(f"\n⚠️  Failed geocoding entries:")
        for entry in failed_geocoding:
            print(f"    - {entry}")

    return len(shipyards) > 0

if __name__ == "__main__":
    success = process_shipyards_csv()
    if not success:
        exit(1)
```

- [ ] **Step 5: Make script executable and run it**

Run: `chmod +x scripts/geocode_shipyards.py && python scripts/geocode_shipyards.py`
Expected: Successfully processes CSV and creates `data/shipyards.json`

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/test_shipyard_integration.py -v`
Expected: All tests PASS with shipyards.json created and properly structured

- [ ] **Step 7: Commit geocoding infrastructure**

```bash
git add scripts/geocode_shipyards.py data/shipyards.json tests/test_shipyard_integration.py
git commit -m "feat: add shipyard CSV geocoding script and test data

- Process Norwegian shipyard CSV with address geocoding
- Generate structured JSON with coordinates and facilities
- Filter out entries without postal codes
- Include comprehensive test coverage"
```

---

### Task 2: Backend Integration

**Files:**
- Modify: `app.py:30,35`
- Add endpoint after line 83

- [ ] **Step 1: Write failing test for shipyard API endpoint**

```python
def test_shipyard_api_endpoint():
    """Test that /api/shipyards endpoint returns shipyard data"""
    # This will be added to test_shipyard_integration.py
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
    # This test ensures graceful handling of missing data
    pass  # Will implement after backend changes
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_shipyard_integration.py::test_shipyard_api_endpoint -v`
Expected: FAIL with "404 NOT FOUND" or "ImportError"

- [ ] **Step 3: Add shipyard loading to app.py startup**

Modify `app.py` after line 30:
```python
# Global state – lastes ved oppstart
_graph = None
_kdtree = None
_node_list = None
_quays_dict = {}
_shipyards = []  # ADD THIS LINE
_startup_error = None
```

Modify `app.py` in startup() function at line 35:
```python
def startup():
    """Laster farled-graf og kai-liste ved oppstart."""
    global _graph, _kdtree, _node_list, _quays_dict, _startup_error, _shipyards  # ADD _shipyards

    # ... existing farled-graf loading code ...

    # --- NSR kaier ---
    try:
        _quays_dict = get_quays_dict()
        print(f"Lastet {len(_quays_dict)} kaier fra NSR", file=sys.stderr)
    except Exception as e:
        print(f"[ADVARSEL] Kunne ikke laste kaier: {e}", file=sys.stderr)

    # --- Shipyards --- ADD THIS SECTION
    try:
        shipyards_path = BASE_DIR / "data" / "shipyards.json"
        if shipyards_path.exists():
            with open(shipyards_path, 'r', encoding='utf-8') as f:
                _shipyards = json.load(f)
            print(f"Lastet {len(_shipyards)} verft fra JSON", file=sys.stderr)
        else:
            print("[INFO] Ingen shipyards.json funnet - verft ikke tilgjengelig", file=sys.stderr)
    except Exception as e:
        print(f"[ADVARSEL] Kunne ikke laste verft: {e}", file=sys.stderr)
        _shipyards = []
```

- [ ] **Step 4: Add shipyard API endpoint**

Add after existing `/api/quays` endpoint around line 83:
```python
@app.route("/api/shipyards")
def get_shipyards():
    """Returnerer liste over tilgjengelige verft for dropdown."""
    return jsonify(_shipyards)
```

- [ ] **Step 5: Test backend changes manually**

Run: `python app.py` then visit `http://localhost:5001/api/shipyards`
Expected: JSON response with shipyard data

- [ ] **Step 6: Run automated tests**

Run: `python -m pytest tests/test_shipyard_integration.py::test_shipyard_api_endpoint -v`
Expected: PASS

- [ ] **Step 7: Commit backend integration**

```bash
git add app.py
git commit -m "feat: add shipyard API endpoint and loading

- Load shipyards.json in startup() following quay pattern
- Add /api/shipyards endpoint returning shipyard list
- Include error handling for missing/invalid shipyard data
- Maintain backward compatibility when shipyards unavailable"
```

---

### Task 3: Frontend Dropdown Integration

**Files:**
- Modify: `templates/index.html:459-464,726-747`

- [ ] **Step 1: Write failing test for frontend shipyard loading**

```python
def test_frontend_shipyard_integration():
    """Test that frontend can load and display shipyards"""
    # This test will use Playwright to verify frontend integration
    # For now, we'll implement manually and verify in browser
    pass  # Manual verification step below
```

- [ ] **Step 2: Add allShipyards variable and extend loadQuays function**

Add `allShipyards` variable near line 292 after `allQuays`:
```javascript
// ─── State ────────────────────────────────────────────────────
let allQuays = [];
let allShipyards = [];  // ADD THIS LINE
```

Modify `loadQuays()` function at line 459-464:
```javascript
async function loadQuays() {
  try {
    const [quaysResponse, shipyardsResponse] = await Promise.all([
      fetch('/api/quays'),
      fetch('/api/shipyards')
    ]);

    allQuays = await quaysResponse.json();
    allShipyards = await shipyardsResponse.json();
    console.log(`Loaded ${allQuays.length} quays and ${allShipyards.length} shipyards`);
  } catch (e) {
    console.error('Failed to load data:', e);
    allShipyards = [];  // Ensure empty array on failure
  }
}
```

- [ ] **Step 3: Add shipyard item builder function**

Add after `buildAddrItem` function around line 720:
```javascript
  function buildShipyardItem(s) {
    const el = document.createElement('div');
    el.className = 'dd-item';

    const name = document.createElement('div');
    name.className = 'dd-item-name';
    name.textContent = s.name;

    const sub = document.createElement('div');
    sub.className = 'dd-item-sub';
    sub.textContent = s.city;

    el.appendChild(name);
    el.appendChild(sub);

    el.addEventListener('mousedown', e => {
      e.preventDefault();
      inp.value = s.name;
      inp.classList.remove('pinned');
      setPoint(which, {
        lat: s.lat,
        lon: s.lon,
        name: s.name,
        shipyard: s  // Include full shipyard data for callout
      });
      close();

      // Apply same UI cleanup fixes as other dropdown items
      setTimeout(() => {
        document.querySelectorAll('.dropdown.open').forEach(dd => dd.classList.remove('open'));
        updateClearBtn(which);
        updateBtn();
      }, 50);
    });

    return el;
  }
```

- [ ] **Step 4: Add facility name formatting function**

Add after `buildShipyardItem`:
```javascript
  function formatFacilityName(key) {
    const mapping = {
      'homepage': 'Hjemmeside',
      'postalCode': 'Postnummer',
      'quay': 'Kai',
      'docksDry': 'Tørrdokk',
      'towingDockSlip': 'Slipeanlegg',
      'docksWet': 'Våtdokk',
      'hall': 'Hall',
      'heatedHall': 'Oppvarmet hall',
      'crane': 'Kran'
    };
    return mapping[key] || key;
  }
```

- [ ] **Step 5: Integrate shipyards into render function**

Modify `render` function around line 726-747:
```javascript
  function render(quays, addrs) {
    while (dd.firstChild) dd.removeChild(dd.firstChild);
    const frag = document.createDocumentFragment();
    const steder  = addrs.filter(a => a.is_sted);
    const vanlige = addrs.filter(a => !a.is_sted);

    // Existing: Kaier section
    if (quays.length) {
      frag.appendChild(buildSection('Kaier (NSR)'));
      quays.slice(0, 20).forEach(q => frag.appendChild(buildQuayItem(q)));
    }

    // NEW: Verft section (between kaier and steder)
    const ql = inp.value.trim().toLowerCase();
    const shipyardMatches = allShipyards.filter(s =>
      s.name.toLowerCase().includes(ql)
    );
    if (shipyardMatches.length) {
      frag.appendChild(buildSection('Verft'));
      shipyardMatches.slice(0, 10).forEach(s => frag.appendChild(buildShipyardItem(s)));
    }

    // Existing: Steder section
    if (steder.length) {
      frag.appendChild(buildSection('Steder'));
      steder.forEach(a => frag.appendChild(buildAddrItem(a)));
    }

    // Existing: Adresser section
    if (vanlige.length) {
      frag.appendChild(buildSection('Adresser'));
      vanlige.forEach(a => frag.appendChild(buildAddrItem(a)));
    }

    if (!quays.length && !shipyardMatches.length && !addrs.length) {
      close();
      return;
    }

    dd.appendChild(frag);
    dd.classList.add('open');
    focusIdx = -1;
  }
```

- [ ] **Step 6: Test frontend integration manually**

Run: `python app.py` and test in browser:
- Type "Fosen" in FROM field → should show "Fosen Yards AS" in Verft section
- Type "Bergen" → should show any Bergen shipyards
- Click on a shipyard → should set coordinates and display name

Expected: Shipyards appear between Kaier and Steder sections

- [ ] **Step 7: Commit frontend dropdown integration**

```bash
git add templates/index.html
git commit -m "feat: integrate shipyard search into dropdown UI

- Extend loadQuays to fetch shipyards in parallel
- Add buildShipyardItem function following existing patterns
- Insert Verft section between Kaier and Steder in dropdown
- Include facility name formatting for Norwegian labels
- Apply same UI cleanup fixes as other dropdown items"
```

---

### Task 4: Enhanced Callout with Facility Information

**Files:**
- Modify: `templates/index.html:546-555` (setPoint function)

- [ ] **Step 1: Write test for enhanced callout**

```python
def test_shipyard_callout_content():
    """Test that shipyard callouts show facility information"""
    # Manual verification test - check in browser that clicking
    # a shipyard point shows facility information in popup
    pass
```

- [ ] **Step 2: Enhance setPoint function for shipyard callouts**

Modify `setPoint` function around line 546-555:
```javascript
function setPoint(which, pt) {
  // Existing compatibility and global variable setting...
  if (which === 'from') fromPoint = pt;
  else if (which === 'to') toPoint = pt;
  else stopPoints[which] = pt;
}

// ADD NEW FUNCTION for enhanced popup creation
function createShipyardPopup(pt) {
  if (!pt || !pt.shipyard) {
    return `Fra: ${pt ? pt.name : 'Unknown location'}`;  // Default popup for non-shipyard points
  }

  const shipyard = pt.shipyard;
  const facilities = shipyard.facilities || {};

  // Build facility information
  const facilityEntries = Object.entries(facilities)
    .filter(([key, value]) => {
      // Skip empty values and main data fields
      if (!value || value === 'No' || key === 'postalCode') return false;
      return true;
    })
    .map(([key, value]) => {
      const displayName = (typeof formatFacilityName === 'function') ? formatFacilityName(key) : key;
      return `${displayName}: ${value}`;
    });

  const facilityInfo = facilityEntries.length > 0
    ? `<br><br><strong>Fasiliteter:</strong><br>${facilityEntries.join('<br>')}`
    : '';

  const homepage = facilities.homepage && facilities.homepage.startsWith('http')
    ? `<br><a href="${facilities.homepage}" target="_blank">Hjemmeside</a>`
    : '';

  return `
    <div class="shipyard-popup">
      <strong>${shipyard.name}</strong><br>
      ${shipyard.address}${homepage}${facilityInfo}
    </div>
  `;
}
```

- [ ] **Step 3: Update pin marker creation to use enhanced popups**

Modify the map click handler around line 500-510:
```javascript
map.on('click', e => {
  if (!pinMode) return;
  const { lat, lng } = e.latlng;
  const label = `${lat.toFixed(4)}, ${lng.toFixed(4)}`;

  setPoint(pinMode, { lat, lon: lng, name: label });

  // Enhanced popup creation
  const popupContent = createShipyardPopup({ lat, lon: lng, name: label });

  if (pinMode === 'from') {
    if (pinMarkerFrom) map.removeLayer(pinMarkerFrom);
    pinMarkerFrom = L.marker([lat, lng], { icon: pinIcon('#3ecfcc') })
      .bindPopup(popupContent).addTo(map);
    if (!toPoint) { setPinMode('to'); return; }
  } else if (pinMode === 'to') {
    if (pinMarkerTo) map.removeLayer(pinMarkerTo);
    pinMarkerTo = L.marker([lat, lng], { icon: pinIcon('#c4965a') })
      .bindPopup(popupContent).addTo(map);
  } else {
    if (stopPinMarkers[pinMode]) map.removeLayer(stopPinMarkers[pinMode]);
    stopPinMarkers[pinMode] = L.marker([lat, lng], { icon: pinIcon('#a0a0a0') })
      .bindPopup(popupContent).addTo(map);
  }

  // ... existing pin mode and UI cleanup code ...
});
```

- [ ] **Step 4: Update dropdown selection to create enhanced markers**

Modify the `buildShipyardItem` mousedown event (from Task 3):
```javascript
el.addEventListener('mousedown', e => {
  e.preventDefault();
  inp.value = s.name;
  inp.classList.remove('pinned');

  // Set point with shipyard data
  const pointData = {
    lat: s.lat,
    lon: s.lon,
    name: s.name,
    shipyard: s
  };
  setPoint(which, pointData);

  // Create enhanced marker with facility popup
  const popupContent = createShipyardPopup(pointData);

  if (which === 'from') {
    if (window.pinMarkerFrom) map.removeLayer(window.pinMarkerFrom);
    window.pinMarkerFrom = L.marker([s.lat, s.lon], { icon: pinIcon('#3ecfcc') })
      .bindPopup(popupContent).addTo(map);
  } else if (which === 'to') {
    if (window.pinMarkerTo) map.removeLayer(window.pinMarkerTo);
    window.pinMarkerTo = L.marker([s.lat, s.lon], { icon: pinIcon('#c4965a') })
      .bindPopup(popupContent).addTo(map);
  } else {
    if (window.stopPinMarkers[which]) map.removeLayer(window.stopPinMarkers[which]);
    window.stopPinMarkers[which] = L.marker([s.lat, s.lon], { icon: pinIcon('#a0a0a0') })
      .bindPopup(popupContent).addTo(map);
  }

  close();

  // Apply UI cleanup fixes
  setTimeout(() => {
    document.querySelectorAll('.dropdown.open').forEach(dd => dd.classList.remove('open'));
    updateClearBtn(which);
    updateBtn();
  }, 50);
});
```

- [ ] **Step 5: Add CSS styling for shipyard popup**

Add CSS in the style section around line 150:
```css
.shipyard-popup {
  font-size: 12px;
  min-width: 200px;
  max-width: 300px;
}

.shipyard-popup strong {
  color: #2c3e50;
  font-size: 14px;
}

.shipyard-popup a {
  color: #3498db;
  text-decoration: none;
}

.shipyard-popup a:hover {
  text-decoration: underline;
}
```

- [ ] **Step 6: Test enhanced callouts manually**

Run: `python app.py` and test:
- Search and select "Fosen Yards AS"
- Click on the marker → should show detailed facility information
- Verify homepage link works if present
- Test with different shipyards to ensure all facilities display correctly

Expected: Rich popup with name, address, homepage link, and formatted facility details

- [ ] **Step 7: Commit enhanced callout feature**

```bash
git add templates/index.html
git commit -m "feat: add enhanced shipyard callouts with facility info

- Create createShipyardPopup function for rich facility display
- Update marker creation to use enhanced popups
- Include facility name mapping for Norwegian labels
- Add CSS styling for professional popup appearance
- Support homepage links and facility details"
```

---

### Task 5: Integration Testing and Validation

**Files:**
- Enhance: `tests/test_shipyard_integration.py`
- Create: `tests/test_shipyard_manual.md`

- [ ] **Step 1: Add comprehensive integration tests**

```python
def test_end_to_end_shipyard_workflow():
    """Test complete shipyard workflow from CSV to frontend"""
    import subprocess
    import time

    # Verify CSV processing
    result = subprocess.run(['python', 'scripts/geocode_shipyards.py'],
                          capture_output=True, text=True)
    assert result.returncode == 0, f"Geocoding script failed: {result.stderr}"

    # Verify JSON file creation
    shipyards_path = Path("data/shipyards.json")
    assert shipyards_path.exists(), "shipyards.json should be created"

    # Verify JSON structure
    with open(shipyards_path) as f:
        shipyards = json.load(f)
    assert len(shipyards) > 5, "Should have multiple shipyards after processing"

    # Test API endpoint
    from app import app
    app.config['TESTING'] = True
    client = app.test_client()

    response = client.get('/api/shipyards')
    assert response.status_code == 200
    api_data = response.get_json()
    assert len(api_data) == len(shipyards), "API should return same data as JSON"

def test_shipyard_search_performance():
    """Test that shipyard search performs adequately"""
    import time

    # Load shipyards
    with open("data/shipyards.json") as f:
        shipyards = json.load(f)

    # Simulate frontend search
    start_time = time.time()
    matches = [s for s in shipyards if 'fosen' in s['name'].lower()]
    search_time = time.time() - start_time

    assert search_time < 0.1, "Search should be fast (<100ms)"
    assert len(matches) > 0, "Should find Fosen Yards"

def test_data_quality_validation():
    """Validate quality of processed shipyard data"""
    with open("data/shipyards.json") as f:
        shipyards = json.load(f)

    for shipyard in shipyards:
        # Validate coordinates are in Norway
        lat, lon = shipyard['lat'], shipyard['lon']
        assert 58 <= lat <= 72, f"Latitude {lat} should be in Norway range"
        assert 4 <= lon <= 32, f"Longitude {lon} should be in Norway range"

        # Validate required fields
        assert shipyard['name'], "Name should not be empty"
        assert shipyard['city'], "City should not be empty"
        assert shipyard['facilities']['postalCode'], "Postal code required"
```

- [ ] **Step 2: Create manual testing guide**

```markdown
# Manual Testing Guide for Shipyard Integration

## Test Scenarios

### 1. Basic Search Functionality
- [ ] Open application in browser
- [ ] Type "Fosen" in FROM field
- [ ] Verify "Verft" section appears between "Kaier" and "Steder"
- [ ] Verify "Fosen Yards AS" shows with "Rissa" subtitle
- [ ] Click on shipyard → verify coordinates set and name displayed

### 2. Search Behavior
- [ ] Test partial name matching: "Bergen" → should show Bergen-area shipyards
- [ ] Test case insensitive: "FOSEN" → should match "Fosen Yards AS"
- [ ] Test no matches: "Nonexistent" → Verft section should not appear
- [ ] Test mixed results: "Verft" → should show shipyards + other results

### 3. Dropdown Positioning
- [ ] Search with results in all categories
- [ ] Verify order: Kaier → Verft → Steder → Adresser
- [ ] Verify section headers appear correctly
- [ ] Verify max 10 shipyards shown per search

### 4. Enhanced Callouts
- [ ] Select shipyard from dropdown
- [ ] Click on shipyard marker
- [ ] Verify popup shows: name, address, homepage link, facilities
- [ ] Test homepage link opens in new tab
- [ ] Verify Norwegian facility labels (Tørrdokk, Kran, etc.)

### 5. Route Calculation
- [ ] Set FROM point as shipyard
- [ ] Set TO point as regular address
- [ ] Verify route calculation triggers correctly
- [ ] Test with waypoint: FROM → shipyard waypoint → TO

### 6. UI State Management
- [ ] Select shipyard → verify dropdown closes properly
- [ ] Verify clear button appears and works
- [ ] Test reset functionality clears shipyard points
- [ ] Verify no "kjøre seg fast" issues with shipyard selection

## Expected Results

- ✅ All searches complete within 200ms
- ✅ No JavaScript errors in console
- ✅ Shipyards integrate seamlessly with existing UI
- ✅ Enhanced callouts show facility information
- ✅ Route calculation works with shipyard coordinates
```

- [ ] **Step 3: Run comprehensive test suite**

Run: `python -m pytest tests/test_shipyard_integration.py -v`
Expected: All tests PASS

- [ ] **Step 4: Perform manual testing**

Follow manual testing guide and verify all scenarios pass

- [ ] **Step 5: Test with multiple browsers**

Test in Chrome, Firefox, Safari to ensure compatibility

- [ ] **Step 6: Performance validation**

Test with large search results and verify responsive performance

- [ ] **Step 7: Commit final integration and tests**

```bash
git add tests/
git commit -m "test: add comprehensive shipyard integration testing

- End-to-end workflow testing from CSV to frontend
- Performance validation for search operations
- Data quality validation for geocoded results
- Manual testing guide for UI verification
- Browser compatibility validation"
```

---

## Implementation Notes

**Dependencies:**
- No new Python packages required (uses urllib, json, csv from stdlib)
- Kartverket geocoding API (same as existing app usage)
- Existing Leaflet.js and dropdown infrastructure

**Data Processing:**
- One-time geocoding script generates static JSON file
- Rate-limited API calls (0.5s between requests)
- Graceful handling of geocoding failures

**Integration Strategy:**
- Follows existing allQuays loading pattern exactly
- Uses same dropdown section architecture
- Applies identical UI state management fixes
- Maintains backward compatibility

**Testing Approach:**
- TDD with failing tests written first
- Manual browser testing for UI verification
- Performance validation for search operations
- Data quality checks for geocoded coordinates

**Deployment:**
- Run geocoding script once to generate shipyards.json
- Commit JSON file to git for consistent deployments
- No runtime dependencies on external geocoding

**Future Enhancements:**
- Facility-based filtering (search by "tørrdokk", "kran")
- Advanced search combining facilities + location
- Real-time shipyard data integration
- Shipyard capacity and services expansion