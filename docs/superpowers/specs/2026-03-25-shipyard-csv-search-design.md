# Shipyard CSV Search Integration Design

## Overview

This design adds Norwegian shipyard search functionality to the sjøvei route calculator by integrating CSV shipyard data into the existing dropdown search system. Shipyards will appear as a new "Verft" section between "Kaier" and "Steder" in the search dropdown.

## Requirements Summary

- **Data Source**: Existing `Verftoversikt-Oversikt Verksted(1).csv` file with Norwegian shipyards
- **Display Format**: Name + City ("Fosen Yards AS" + "Rissa" as subtitle)
- **Search Behavior**: Match only on shipyard name
- **Callout Content**: Complete facility information from all CSV columns
- **Data Quality**: Exclude shipyards missing postal codes
- **Position**: "Verft" section between "Kaier (NSR)" and "Steder" in dropdown
- **Coordinates**: Pre-geocode all addresses using Kartverket API

## Architecture

**Approach**: Minimal Backend Integration following existing `allQuays` pattern

The solution extends the current dropdown search system with minimal changes to proven code. A preprocessing script geocodes CSV data into JSON format, which is loaded frontend-side like the existing quay data.

## Components

### 1. Data Processing and Structure

**Geocoding Script** (`scripts/geocode_shipyards.py`):
- Reads `Verftoversikt-Oversikt Verksted(1).csv`
- Filters out entries without postal codes
- Geocodes addresses via Kartverket API (same endpoint as main app)
- Outputs structured JSON with coordinates and facility data

**Output Structure** (`data/shipyards.json`):
```json
[
  {
    "name": "Fosen Yards AS",
    "city": "Rissa",
    "address": "Kvithyllveien 171, 7100 Rissa",
    "lat": 63.5678,
    "lon": 10.2345,
    "facilities": {
      "homepage": "https://fosenyard.com/",
      "postalCode": "7100",
      "quay": "350 meter",
      "docksDry": "Yes, 215x40 meter",
      "towingDockSlip": "No",
      "docksWet": "No",
      "hall": "No",
      "heatedHall": "No",
      "crane": "75 tonn, 40, 25, 10"
    }
  }
]
```

**Benefits**: Standard JSON format, easy to load, structured facility data for comprehensive callouts.

### 2. Backend Changes (Minimal)

**Modifications to `app.py`**:

```python
# Add global variable
allShipyards = []

# Extend startup() function
def startup():
    global _graph, _kdtree, _node_list, _quays_dict, _startup_error, allShipyards

    # Existing graph and quay loading...

    # Load shipyards
    try:
        shipyards_path = BASE_DIR / "data" / "shipyards.json"
        if shipyards_path.exists():
            with open(shipyards_path, 'r', encoding='utf-8') as f:
                allShipyards = json.load(f)
    except Exception as e:
        print(f"Warning: Could not load shipyards: {e}", file=sys.stderr)
        allShipyards = []

# Add API endpoint
@app.route("/api/shipyards")
def get_shipyards():
    """Returns list of available shipyards for dropdown."""
    return jsonify(allShipyards)
```

**Error Handling**:
- Missing `shipyards.json` → empty list, no shipyards in dropdown
- Geocoding script failure → existing app functionality unaffected
- API errors → graceful degradation

**Deployment Strategy**:
- Run geocoding script once to generate JSON file
- Commit JSON file to git for consistent deployments
- Script can be re-run if CSV data updates

### 3. Frontend Integration

**Loading and Caching**:
```javascript
// Add global variable alongside allQuays
let allShipyards = [];

// Extend loadQuays() function
async function loadQuays() {
  try {
    const [quaysResponse, shipyardsResponse] = await Promise.all([
      fetch('/api/quays'),
      fetch('/api/shipyards')
    ]);
    allQuays = await quaysResponse.json();
    allShipyards = await shipyardsResponse.json();
  } catch (e) {
    // Existing error handling
  }
}
```

**Dropdown Integration**:
```javascript
function render(quays, addrs) {
  while (dd.firstChild) dd.removeChild(dd.firstChild);
  const frag = document.createDocumentFragment();
  const steder = addrs.filter(a => a.is_sted);
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

  // Existing: Steder and Adresser sections...
}
```

**Shipyard Item Builder**:
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

**Callout Enhancement**:
When a shipyard point is selected, enhance marker popup to show complete facility information:

```javascript
// In setPoint function, check for shipyard data
function setPoint(which, pt) {
  // Existing point setting logic...

  // Enhanced popup for shipyards
  if (pt.shipyard) {
    const facilities = pt.shipyard.facilities;
    const facilityInfo = Object.entries(facilities)
      .filter(([key, value]) => value && value !== 'No')
      .map(([key, value]) => `${formatFacilityName(key)}: ${value}`)
      .join('<br>');

    const popupContent = `
      <div class="shipyard-popup">
        <strong>${pt.shipyard.name}</strong><br>
        ${pt.shipyard.address}<br>
        <a href="${facilities.homepage}" target="_blank">Hjemmeside</a><br>
        <br>
        <strong>Fasiliteter:</strong><br>
        ${facilityInfo}
      </div>
    `;

    // Apply popup to appropriate marker
    if (which === 'from' && pinMarkerFrom) {
      pinMarkerFrom.bindPopup(popupContent);
    }
    // ... similar for other markers
  }
}
```

### 4. Testing and Error Handling

**Geocoding Script Validation**:
- Verify all addresses receive coordinates
- Log failed geocoding attempts for manual review
- Check for and handle duplicate entries
- Validate postal code presence before processing

**Frontend Testing Scenarios**:
- Search for known shipyard names ("Fosen", "Bergen") → verify correct results
- Click on shipyard → verify coordinates set and route calculation triggered
- Callout display → verify all facility information appears correctly
- Mixed search → verify shipyards appear between kaier and steder

**Error Handling Strategy**:
- Geocoding failures → skip problematic entry, continue processing others
- Missing shipyards.json → empty allShipyards array, no "Verft" section shown
- API errors → graceful degradation, existing search functionality preserved
- Invalid shipyard data → validate structure, exclude malformed entries

**Compatibility Assurance**:
- No modifications to existing kai/adresse/pin functionality
- Preserve existing UI state management fixes ("kjøre seg fast" solutions)
- No breaking changes to current workflows
- Maintain same search performance characteristics

## Data Flow

1. **Preprocessing**: CSV → geocoding script → `data/shipyards.json`
2. **App startup**: Load shipyards.json into memory alongside quays
3. **Frontend load**: Fetch shipyards via `/api/shipyards` endpoint
4. **Search**: Filter shipyards by name match, display in "Verft" section
5. **Selection**: Set point with coordinates and shipyard metadata
6. **Route calculation**: Proceed with normal routing using coordinates

## Benefits

- **Minimal risk**: Follows proven patterns from existing quay system
- **Fast implementation**: Leverages existing dropdown infrastructure
- **User familiar**: Same search UX as current kaier/steder/adresser
- **Comprehensive data**: Rich facility information in callouts
- **Performance**: Pre-geocoded coordinates for instant route calculation
- **Maintainable**: Simple data update process via script re-run

## Integration Points

- Extends existing `makeSearch` dropdown system
- Uses same `setPoint()` architecture for route calculation
- Applies identical UI state management fixes
- Follows established API patterns (`/api/quays` → `/api/shipyards`)
- Maintains existing error handling and loading strategies

## Future Enhancements

- **Facility filtering**: Search by specific facility types (crane, dry dock, etc.)
- **Capacity data**: Add detailed specifications for facilities
- **Real-time updates**: API integration with shipyard management systems
- **Favorite shipyards**: User preference storage
- **Advanced search**: Combined facility + location search capabilities