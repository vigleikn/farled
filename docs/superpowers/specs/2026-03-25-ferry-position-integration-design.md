# Ferry Position Integration Design

## Overview

This design adds Norwegian ferry position integration to the sjøvei route calculator, allowing users to select live ferry positions as route starting points. Users can click on any of 90 predefined Norwegian coastal ferries to use their current position as the "Fra" (from) point for route planning.

## Requirements Summary

- **Data Source**: Predefined list of 90 Norwegian ferries with MMSI numbers
- **Position Data**: Current ferry positions from Barentswatch AIS API
- **User Interaction**: Click ferry markers to set as route starting point
- **Information Display**: Minimal - ferry name only in popup
- **Update Strategy**: Static snapshot on page load, no real-time updates
- **Integration**: Follows existing shipyard CSV processing pattern

## Architecture

**Approach**: Ferry CSV Processing following proven shipyard pattern

The solution extends the current route planning system by adding ferries as a third data source alongside quays and shipyards. A preprocessing script queries ferry positions and outputs static JSON data that is loaded frontend-side.

## Components

### 1. Data Processing and Structure

**Ferry Processing Script** (`scripts/process_ferries.py`):
- Reads predefined ferry CSV list (name, IMO, MMSI)
- Filters out entries without valid MMSI numbers
- Queries Barentswatch AIS API for current positions of each valid MMSI
- Handles API authentication and rate limiting (0.5s between requests)
- Outputs structured JSON with ferry details and current coordinates

**CSV Input Structure**:
```
Navn,IMO-nummer,MMSI-nummer
BASTØ ELECTRIC,9878993,257122880
BASTØ I,9144081,259401000
...
```

**Output Structure** (`data/ferries.json`):
```json
[
  {
    "name": "BASTØ ELECTRIC",
    "imo": "9878993",
    "mmsi": "257122880",
    "lat": 59.123,
    "lon": 10.456,
    "lastUpdate": "2026-03-25T10:30:00Z"
  }
]
```

**Benefits**: Standard JSON format, easy to load, handles missing MMSIs gracefully like shipyard postal code filtering.

### 2. Backend Changes (Minimal)

**Modifications to `app.py`**:

```python
# Add global variable
allFerries = []

# Extend startup() function
def startup():
    global _graph, _kdtree, _node_list, _quays_dict, allShipyards, allFerries

    # Existing graph, quay, and shipyard loading...

    # Load ferries
    try:
        ferries_path = BASE_DIR / "data" / "ferries.json"
        if ferries_path.exists():
            with open(ferries_path, 'r', encoding='utf-8') as f:
                allFerries = json.load(f)
    except Exception as e:
        print(f"Warning: Could not load ferries: {e}", file=sys.stderr)
        allFerries = []

# Add API endpoint
@app.route("/api/ferries")
def get_ferries():
    """Returns list of ferry positions for route planning."""
    return jsonify(allFerries)
```

**Error Handling**:
- Missing `ferries.json` → empty list, no ferry markers displayed
- Processing script failure → existing app functionality unaffected
- API errors → graceful degradation

**Deployment Strategy**:
- Run processing script once to generate JSON file
- Commit JSON file to git for consistent deployments
- Script can be re-run to update ferry positions

### 3. Frontend Integration

**Loading and Caching**:
```javascript
// Add global variable alongside allQuays, allShipyards
let allFerries = [];

// Extend loadQuays() function for parallel loading
async function loadQuays() {
  try {
    const [quaysResponse, shipyardsResponse, ferriesResponse] = await Promise.all([
      fetch('/api/quays'),
      fetch('/api/shipyards'),
      fetch('/api/ferries')
    ]);
    allQuays = await quaysResponse.json();
    allShipyards = await shipyardsResponse.json();
    allFerries = await ferriesResponse.json();
    console.log(`Loaded ${allQuays.length} quays, ${allShipyards.length} shipyards, ${allFerries.length} ferries`);
  } catch (e) {
    console.error('Failed to load data:', e);
    allFerries = [];
  }
}
```

**Ferry Marker Creation**:
```javascript
function createFerryMarkers() {
  allFerries.forEach(ferry => {
    const marker = L.marker([ferry.lat, ferry.lon], {
      icon: shipIcon() // Distinct ship icon
    })
    .bindPopup(ferry.name) // Minimal - name only
    .on('click', () => {
      setPoint('from', {
        lat: ferry.lat,
        lon: ferry.lon,
        name: ferry.name,
        ferry: ferry // Include ferry data
      });
      document.getElementById('from-input').value = ferry.name;
      updateClearBtn('from');
      updateBtn();
    })
    .addTo(map);
  });
}
```

**Route Planning Integration**:
- Ferry positions work as route starting points only
- Click ferry → sets as "Fra" (from) point for route planning
- Standard route calculation from ferry coordinates to selected destination
- Ferry name appears in "Fra" input field when selected

### 4. User Experience and Interaction

**User Workflow**:
1. **Page loads** → 90 Norwegian ferries appear as ship icons on map
2. **Click ferry** → Ferry name populates "Fra" input field, ferry position set as route start
3. **Select destination** → Use existing dropdown (quays/shipyards/addresses) or map pin
4. **Route calculates** → Standard sea route from ferry's current position to destination

**Visual Design**:
- **Ferry icons**: Ship-shaped markers distinct from pins/shipyard markers
- **Ferry popup**: Minimal - just ferry name (e.g., "BASTØ ELECTRIC")
- **Integration**: Ferries visible alongside existing markers, no separate controls
- **Color coding**: Ferries use distinct color vs. pins and shipyards

**Information Display**:
- **Map markers**: Ferry name only (minimal approach)
- **Route panel**: Shows "Fra: [Ferry Name]" → "Til: [Destination]"
- **No real-time updates**: Static positions until page refresh

### 5. Testing and Error Handling

**Ferry Processing Validation**:
- Verify all valid MMSIs receive positions from Barentswatch API
- Log failed position lookups for manual review
- Handle missing MMSI numbers (skip like shipyards without postal codes)
- Validate coordinate bounds for Norwegian waters

**Frontend Testing Scenarios**:
- Click ferry markers → verify position sets correctly as route start
- Route calculation → verify standard routing from ferry coordinates
- Mixed selection → verify ferries work with existing quay/shipyard destinations
- Error states → verify graceful handling of missing ferry data

**Error Handling Strategy**:
- API authentication failures → clear error message, script exits cleanly
- Missing ferry positions → skip problematic entries, continue processing others
- Missing ferries.json → empty allFerries array, no ferry markers shown
- Invalid ferry data → validate structure, exclude malformed entries

**Production Resilience**:
- **Barentswatch API limits**: Rate limiting with 0.5s delays between requests
- **Network timeouts**: Individual ferry timeouts don't stop processing
- **Stale positions**: Acceptable for route planning (positions may be hours old)

**Compatibility Assurance**:
- No modifications to existing route calculation logic
- Preserve existing quay/shipyard/address functionality
- Ferry markers use independent marker management
- Follow established error handling patterns

## Data Flow

1. **Preprocessing**: CSV ferry list → Barentswatch API queries → `data/ferries.json`
2. **App startup**: Load ferries.json into memory alongside quays/shipyards
3. **Frontend load**: Fetch ferries via `/api/ferries` endpoint in parallel with other data
4. **Map display**: Create ferry markers with ship icons
5. **User interaction**: Click ferry → set as route start point
6. **Route calculation**: Standard routing using ferry coordinates

## Benefits

- **Minimal risk**: Follows proven shipyard CSV processing pattern
- **Fast implementation**: Leverages existing infrastructure
- **User familiar**: Same route planning UX as current system
- **Performance**: Static positions suitable for route planning use case
- **Maintainable**: Simple data update process via script re-run
- **Focused dataset**: 90 specific ferries vs. hundreds of random vessels

## Integration Points

- Extends existing `loadQuays()` data loading system
- Uses same `setPoint()` architecture for route calculation
- Applies identical error handling and graceful degradation
- Follows established API patterns (`/api/quays` → `/api/shipyards` → `/api/ferries`)
- Maintains existing marker and popup management strategies

## Future Enhancements

- **Position refresh**: Manual refresh button to update ferry positions
- **Ferry details**: Expand popup to show destination, ETA, vessel type
- **Route history**: Track commonly used ferry-to-destination routes
- **Periodic updates**: Automated ferry position updates (hourly/daily)
- **Ferry filtering**: Show/hide ferries by route or operator