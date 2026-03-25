# Ship Position Tracking and Shipyard Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add live ship position selection via Barentswatch AIS and shipyard selection from CSV data to the sjøvei sea route calculator.

**Architecture:** Extend existing point selection system with two new modes: AIS ship position picker that integrates with Barentswatch live data, and shipyard selector that loads from static CSV. Both integrate seamlessly with current FROM/TO/waypoint workflow.

**Tech Stack:** Flask backend, Barentswatch AIS API, CSV parsing, Leaflet.js frontend, existing dropdown system

---

## File Structure Analysis

**New Files:**
- `data/shipyards.csv` - Static shipyard address data
- `static/js/ship-position.js` - AIS integration and ship selection UI
- `static/js/shipyard-loader.js` - CSV parsing and shipyard search
- `tests/test_ais_integration.py` - AIS API integration tests
- `tests/test_shipyard_data.py` - CSV loading and search tests

**Modified Files:**
- `app.py` - Add AIS proxy endpoint and shipyard data endpoint
- `templates/index.html` - Add ship position and shipyard UI elements
- `static/css/style.css` - Styling for new UI components (if needed)

---

### Task 1: Shipyard CSV Data Structure and Loading

**Files:**
- Create: `data/shipyards.csv`
- Create: `tests/test_shipyard_data.py`
- Modify: `app.py:12-15` (add import for CSV handling)

- [ ] **Step 1: Write the failing test for CSV loading**

```python
import pytest
from app import load_shipyards

def test_load_shipyards_returns_list():
    shipyards = load_shipyards()
    assert isinstance(shipyards, list)
    assert len(shipyards) > 0

def test_shipyard_structure():
    shipyards = load_shipyards()
    shipyard = shipyards[0]
    required_fields = ['name', 'lat', 'lon', 'municipality', 'type']
    for field in required_fields:
        assert field in shipyard
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_shipyard_data.py::test_load_shipyards_returns_list -v`
Expected: FAIL with "ImportError: cannot import name 'load_shipyards'"

- [ ] **Step 3: Create sample shipyard CSV data**

```csv
name,lat,lon,municipality,type,address
Bergen Engines,60.3913,5.3221,Bergen,Engine Repair,Kokstadveien 23
Ulstein Verft,62.3467,6.0895,Ørsta,Shipbuilding,Sjøholt
Kleven Verft,62.4567,6.1234,Ulsteinvik,Shipbuilding,Kleven Maritime AS
Fosen Yard,63.5678,10.2345,Rissa,Ship Repair,Fosen Yard AS
```

- [ ] **Step 4: Implement CSV loader in app.py**

```python
import csv
import os

def load_shipyards():
    """Load shipyard data from CSV file"""
    shipyards = []
    csv_path = os.path.join('data', 'shipyards.csv')

    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                shipyards.append({
                    'name': row['name'],
                    'lat': float(row['lat']),
                    'lon': float(row['lon']),
                    'municipality': row['municipality'],
                    'type': row['type'],
                    'address': row.get('address', '')
                })
    except FileNotFoundError:
        print(f"Warning: {csv_path} not found")

    return shipyards
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_shipyard_data.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add data/shipyards.csv tests/test_shipyard_data.py app.py
git commit -m "feat: add shipyard CSV data loading"
```

---

### Task 2: Shipyard Search API Endpoint

**Files:**
- Modify: `app.py` (add shipyard endpoint after quays endpoint ~line 180)
- Create: `tests/test_shipyard_api.py`

- [ ] **Step 1: Write the failing test for shipyard API**

```python
import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    return app.test_client()

def test_shipyard_search_endpoint(client):
    response = client.get('/api/shipyards?q=Bergen')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)

def test_shipyard_search_filters_by_query(client):
    response = client.get('/api/shipyards?q=Bergen')
    data = response.get_json()

    # Should contain Bergen-related results
    bergen_results = [s for s in data if 'Bergen' in s['name'] or 'Bergen' in s['municipality']]
    assert len(bergen_results) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_shipyard_api.py::test_shipyard_search_endpoint -v`
Expected: FAIL with "404 NOT FOUND"

- [ ] **Step 3: Implement shipyard search endpoint**

```python
@app.route('/api/shipyards')
def search_shipyards():
    """Search shipyards by name or municipality"""
    query = request.args.get('q', '').lower()

    if len(query) < 2:
        return jsonify([])

    shipyards = load_shipyards()

    # Filter shipyards by query
    results = []
    for shipyard in shipyards:
        if (query in shipyard['name'].lower() or
            query in shipyard['municipality'].lower() or
            query in shipyard.get('type', '').lower()):
            results.append(shipyard)

    # Limit results to 10
    return jsonify(results[:10])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_shipyard_api.py -v`
Expected: PASS

- [ ] **Step 5: Test manually in browser**

Run: `python app.py` then visit `http://localhost:5001/api/shipyards?q=Bergen`
Expected: JSON response with shipyard data

- [ ] **Step 6: Commit**

```bash
git add tests/test_shipyard_api.py app.py
git commit -m "feat: add shipyard search API endpoint"
```

---

### Task 3: AIS Integration Research and Proxy Endpoint

**Files:**
- Create: `tests/test_ais_integration.py`
- Modify: `app.py` (add AIS proxy endpoint)

- [ ] **Step 1: Research Barentswatch AIS API structure**

Visit: `https://live.ais.barentswatch.no/index.html`
Goal: Understand API endpoints and data structure
Document: Available endpoints, authentication, rate limits

- [ ] **Step 2: Write failing test for AIS proxy**

```python
import pytest
import responses
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    return app.test_client()

@responses.activate
def test_ais_proxy_endpoint(client):
    # Mock the external AIS API
    responses.add(
        responses.GET,
        'https://www.barentswatch.no/api/v1/geodata/ais',
        json=[{
            'mmsi': 123456789,
            'name': 'TEST SHIP',
            'latitude': 59.9139,
            'longitude': 10.7522,
            'course': 180,
            'speed': 12.5
        }],
        status=200
    )

    response = client.get('/api/ais?bbox=10,59,11,60')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert 'mmsi' in data[0]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_ais_integration.py::test_ais_proxy_endpoint -v`
Expected: FAIL with "404 NOT FOUND"

- [ ] **Step 4: Implement basic AIS proxy endpoint**

```python
import requests
from flask import request, jsonify

@app.route('/api/ais')
def ais_proxy():
    """Proxy AIS data from Barentswatch"""
    # Get bounding box from query params
    bbox = request.args.get('bbox')  # format: "west,south,east,north"

    if not bbox:
        return jsonify({'error': 'bbox parameter required'}), 400

    try:
        # TODO: Replace with actual Barentswatch API endpoint after research
        # This is a placeholder structure
        ais_url = 'https://www.barentswatch.no/api/v1/geodata/ais'
        params = {'bbox': bbox}

        response = requests.get(ais_url, params=params, timeout=10)
        response.raise_for_status()

        return jsonify(response.json())

    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Failed to fetch AIS data'}), 500
```

- [ ] **Step 5: Install requests dependency**

Run: `pip install requests`
Add to requirements.txt: `requests==2.31.0`

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/test_ais_integration.py -v`
Expected: PASS (with mocked response)

- [ ] **Step 7: Commit**

```bash
git add tests/test_ais_integration.py app.py requirements.txt
git commit -m "feat: add AIS proxy endpoint (placeholder)"
```

---

### Task 4: Frontend Shipyard Integration

**Files:**
- Create: `static/js/shipyard-loader.js`
- Modify: `templates/index.html` (add script tag and integrate with dropdown system)

- [ ] **Step 1: Write shipyard integration JavaScript**

```javascript
// static/js/shipyard-loader.js
class ShipyardLoader {
    constructor() {
        this.cache = new Map();
    }

    async searchShipyards(query) {
        if (query.length < 2) return [];

        if (this.cache.has(query)) {
            return this.cache.get(query);
        }

        try {
            const response = await fetch(`/api/shipyards?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            this.cache.set(query, data);
            return data;
        } catch (error) {
            console.error('Failed to fetch shipyards:', error);
            return [];
        }
    }

    formatShipyard(shipyard) {
        return {
            name: shipyard.name,
            subtitle: `${shipyard.type}, ${shipyard.municipality}`,
            lat: shipyard.lat,
            lon: shipyard.lon,
            type: 'shipyard'
        };
    }
}

// Global instance
window.shipyardLoader = new ShipyardLoader();
```

- [ ] **Step 2: Test JavaScript in browser console**

Run: `python app.py` and visit `http://localhost:5001`
Console: `window.shipyardLoader.searchShipyards('Bergen').then(console.log)`
Expected: Array of shipyard objects

- [ ] **Step 3: Integrate shipyards into existing dropdown system**

Modify dropdown render function in `templates/index.html` around line 720:

```javascript
// Add to the render function after addresses section
if (query.length >= 2) {
    const shipyards = await window.shipyardLoader.searchShipyards(query);

    if (shipyards.length > 0) {
        dd.appendChild(buildSection('Verft'));
        shipyards.forEach(shipyard => {
            dd.appendChild(buildShipyardItem(shipyard));
        });
    }
}

function buildShipyardItem(s) {
    const el = document.createElement('div');
    el.className = 'dd-item';
    const name = document.createElement('div');
    name.className = 'dd-item-name';
    name.textContent = s.name;
    const sub = document.createElement('div');
    sub.className = 'dd-item-sub';
    sub.textContent = `${s.type}, ${s.municipality}`;
    el.appendChild(name); el.appendChild(sub);
    el.addEventListener('mousedown', e => {
        e.preventDefault();
        inp.value = s.name;
        inp.classList.remove('pinned');
        setPoint(which, { lat: s.lat, lon: s.lon, name: s.name });
        close();

        // Apply same fixes as other dropdown items
        setTimeout(() => {
            document.querySelectorAll('.dropdown.open').forEach(dd => dd.classList.remove('open'));
            updateClearBtn(which);
        }, 50);
    });
    return el;
}
```

- [ ] **Step 4: Test shipyard search in UI**

Run: Type "Bergen" in FROM input
Expected: Dropdown shows shipyard section with Bergen Engines

- [ ] **Step 5: Commit**

```bash
git add static/js/shipyard-loader.js templates/index.html
git commit -m "feat: integrate shipyard search into dropdown"
```

---

### Task 5: Ship Position UI Implementation

**Files:**
- Create: `static/js/ship-position.js`
- Modify: `templates/index.html` (add ship selection UI elements)

- [ ] **Step 1: Create ship position selection JavaScript**

```javascript
// static/js/ship-position.js
class ShipPositionSelector {
    constructor(map) {
        this.map = map;
        this.shipMarkers = [];
        this.activeShipMode = null;
        this.lastShipData = [];
    }

    async loadShipsInArea(bounds) {
        const bbox = `${bounds.getWest()},${bounds.getSouth()},${bounds.getEast()},${bounds.getNorth()}`;

        try {
            const response = await fetch(`/api/ais?bbox=${bbox}`);
            const ships = await response.json();
            this.lastShipData = ships;
            return ships;
        } catch (error) {
            console.error('Failed to load ship data:', error);
            return [];
        }
    }

    displayShips(ships) {
        // Clear existing ship markers
        this.clearShipMarkers();

        ships.forEach(ship => {
            const marker = L.marker([ship.latitude, ship.longitude], {
                icon: L.divIcon({
                    className: 'ship-marker',
                    html: `<div class="ship-icon">🚢</div>`,
                    iconSize: [20, 20]
                })
            });

            marker.bindPopup(`
                <div class="ship-popup">
                    <strong>${ship.name || 'Unknown Ship'}</strong><br>
                    MMSI: ${ship.mmsi}<br>
                    Speed: ${ship.speed || 0} knots<br>
                    Course: ${ship.course || 0}°
                </div>
            `);

            marker.on('click', () => {
                if (this.activeShipMode) {
                    this.selectShip(ship);
                }
            });

            marker.addTo(this.map);
            this.shipMarkers.push(marker);
        });
    }

    selectShip(ship) {
        const inputEl = document.getElementById(this.activeShipMode + '-input');
        if (!inputEl) return;

        const shipName = ship.name || `Ship ${ship.mmsi}`;
        inputEl.value = `Ship: ${shipName}`;
        inputEl.classList.add('pinned');

        setPoint(this.activeShipMode, {
            lat: ship.latitude,
            lon: ship.longitude,
            name: shipName
        });

        this.exitShipMode();
        updateClearBtn(this.activeShipMode);
    }

    enterShipMode(pointType) {
        this.activeShipMode = pointType;
        document.body.style.cursor = 'crosshair';

        // Load and display ships in current view
        const bounds = this.map.getBounds();
        this.loadShipsInArea(bounds).then(ships => {
            this.displayShips(ships);
        });
    }

    exitShipMode() {
        this.activeShipMode = null;
        document.body.style.cursor = '';
        this.clearShipMarkers();
    }

    clearShipMarkers() {
        this.shipMarkers.forEach(marker => {
            this.map.removeLayer(marker);
        });
        this.shipMarkers = [];
    }
}

// Global instance (initialized after map is ready)
window.shipPositionSelector = null;
```

- [ ] **Step 2: Add ship selection buttons to UI**

Modify `templates/index.html` to add ship buttons next to pin buttons:

```html
<!-- Add after existing pin buttons around line 45 -->
<button type="button" id="from-ship" class="icon-btn" title="Velg skip posisjon">🚢</button>
<!-- Add after to-pin button -->
<button type="button" id="to-ship" class="icon-btn" title="Velg skip posisjon">🚢</button>
```

- [ ] **Step 3: Initialize ship selector and wire up events**

Add to `templates/index.html` after map initialization:

```javascript
// Initialize ship position selector after map is ready
window.shipPositionSelector = new ShipPositionSelector(map);

// Wire up ship selection buttons
document.getElementById('from-ship').addEventListener('click', () => {
    window.shipPositionSelector.enterShipMode('from');
});

document.getElementById('to-ship').addEventListener('click', () => {
    window.shipPositionSelector.enterShipMode('to');
});

// Exit ship mode when other modes are activated
function exitAllModes() {
    if (window.shipPositionSelector) {
        window.shipPositionSelector.exitShipMode();
    }
}

// Call exitAllModes when pin mode is activated
```

- [ ] **Step 4: Add CSS styling for ship markers**

Add to CSS section in `templates/index.html`:

```css
.ship-marker {
    border: none;
    background: none;
}

.ship-icon {
    font-size: 16px;
    filter: drop-shadow(1px 1px 2px rgba(0,0,0,0.5));
}

.ship-popup {
    font-size: 12px;
    min-width: 150px;
}

#from-ship, #to-ship {
    background: #e3f2fd;
    border: 1px solid #2196f3;
}

#from-ship:hover, #to-ship:hover {
    background: #bbdefb;
}
```

- [ ] **Step 5: Test ship selection UI (with mock data)**

Run: `python app.py`
Test: Click ship button, verify UI mode changes
Expected: Cursor changes, ship markers appear (even if API returns empty)

- [ ] **Step 6: Commit**

```bash
git add static/js/ship-position.js templates/index.html
git commit -m "feat: add ship position selection UI"
```

---

### Task 6: Complete AIS Integration

**Files:**
- Modify: `app.py` (update AIS endpoint with real Barentswatch API)
- Create: `docs/ais-api-research.md` (document API findings)

- [ ] **Step 1: Research actual Barentswatch AIS API**

Goal: Find real API endpoints for live AIS data
Document findings in `docs/ais-api-research.md`

- [ ] **Step 2: Update AIS endpoint with real API**

Replace placeholder in `app.py` with actual Barentswatch integration:

```python
@app.route('/api/ais')
def ais_proxy():
    """Proxy AIS data from Barentswatch"""
    bbox = request.args.get('bbox')

    if not bbox:
        return jsonify({'error': 'bbox parameter required'}), 400

    try:
        # Updated with real Barentswatch API endpoint
        # (Replace with actual endpoint discovered in research)
        ais_url = 'https://actual-barentswatch-api.no/ais/vessels'

        params = {
            'bbox': bbox,
            # Add other required parameters based on research
        }

        headers = {
            # Add authentication headers if required
        }

        response = requests.get(ais_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        # Transform API response to our expected format
        ships = []
        for vessel in response.json():
            ships.append({
                'mmsi': vessel.get('mmsi'),
                'name': vessel.get('name'),
                'latitude': vessel.get('lat'),
                'longitude': vessel.get('lon'),
                'course': vessel.get('course'),
                'speed': vessel.get('speed')
            })

        return jsonify(ships)

    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Failed to fetch AIS data', 'details': str(e)}), 500
```

- [ ] **Step 3: Test AIS integration with real data**

Run: Visit `/api/ais?bbox=4,58,32,72` (Norway bounding box)
Expected: Real ship position data (or appropriate error if API requires auth)

- [ ] **Step 4: Handle authentication if required**

If Barentswatch requires API keys:
- Add configuration for API keys
- Update requests to include authentication
- Document setup requirements

- [ ] **Step 5: Test full ship selection workflow**

Run: Full application test
Test: FROM → Ship button → Select visible ship → Verify coordinates
Expected: Ship position selected as route start point

- [ ] **Step 6: Commit**

```bash
git add app.py docs/ais-api-research.md
git commit -m "feat: integrate real Barentswatch AIS API"
```

---

### Task 7: Integration Testing and Documentation

**Files:**
- Create: `tests/test_integration.py`
- Create: `docs/feature-ship-shipyard.md`
- Modify: `README.md` (add feature documentation)

- [ ] **Step 1: Write integration tests**

```python
import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    return app.test_client()

def test_full_shipyard_workflow(client):
    """Test complete shipyard selection workflow"""
    # Test search
    response = client.get('/api/shipyards?q=Bergen')
    assert response.status_code == 200

    shipyards = response.get_json()
    assert len(shipyards) > 0

    # Verify data structure
    shipyard = shipyards[0]
    assert 'name' in shipyard
    assert 'lat' in shipyard
    assert 'lon' in shipyard

def test_ais_integration_error_handling(client):
    """Test AIS endpoint handles errors gracefully"""
    # Test missing bbox
    response = client.get('/api/ais')
    assert response.status_code == 400

    # Test with bbox
    response = client.get('/api/ais?bbox=10,59,11,60')
    # Should either return data or proper error
    assert response.status_code in [200, 500]
```

- [ ] **Step 2: Run integration tests**

Run: `python -m pytest tests/test_integration.py -v`
Expected: PASS

- [ ] **Step 3: Create feature documentation**

```markdown
# Ship Position and Shipyard Selection Features

## Overview

The sjøvei application now supports:
- Live ship position selection via Barentswatch AIS data
- Shipyard selection from static CSV database

## Usage

### Ship Position Selection
1. Click the ship icon (🚢) next to FROM or TO fields
2. Map displays live ships in current view area
3. Click on any ship marker to select its position
4. Ship name and coordinates are set as route point

### Shipyard Selection
1. Type in FROM/TO/waypoint input field
2. Shipyard results appear in dropdown under "Verft" section
3. Select desired shipyard from list
4. Shipyard coordinates are set as route point

## Data Sources

- **Ship Positions**: Live AIS data from Barentswatch
- **Shipyards**: Static CSV database (`data/shipyards.csv`)

## API Endpoints

- `GET /api/ais?bbox=west,south,east,north` - Live ship positions
- `GET /api/shipyards?q=search_term` - Shipyard search
```

- [ ] **Step 4: Update README.md**

Add to README.md features section:

```markdown
## New Features

### 🚢 Live Ship Position Selection
- Select current ship positions as route points using live AIS data
- Integrated with Barentswatch maritime traffic system
- Click ship icon to enter selection mode

### ⚓ Shipyard Database
- Search and select shipyards across Norway
- Static database with major repair facilities and shipbuilders
- Integrated into standard address search workflow
```

- [ ] **Step 5: Test complete feature workflow**

Manual test checklist:
- [ ] Shipyard search works in dropdown
- [ ] Ship selection mode activates correctly
- [ ] Ship markers appear on map
- [ ] Selecting ship sets coordinates
- [ ] Both features integrate with routing
- [ ] No conflicts with existing "kjøre seg fast" fixes

- [ ] **Step 6: Final commit**

```bash
git add tests/test_integration.py docs/feature-ship-shipyard.md README.md
git commit -m "feat: complete ship position and shipyard selection features"
```

---

## Implementation Notes

**Dependencies:**
- `requests` library for AIS API calls
- Barentswatch API access (may require registration)
- CSV file with shipyard data

**Integration Points:**
- Extends existing `setPoint()` system
- Uses same dropdown architecture as addresses/quays
- Applies same UI state management fixes

**Testing Strategy:**
- Mock external APIs for unit tests
- Integration tests for complete workflows
- Manual testing for UI interactions

**Future Enhancements:**
- Ship filtering by type/size
- Real-time ship movement updates
- Shipyard capacity/services data
- Favorite ships/shipyards