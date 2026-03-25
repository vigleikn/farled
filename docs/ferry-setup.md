# Ferry Integration Setup Guide

## Overview

The sjøvei route calculator integrates live Norwegian ferry position data from the Barentswatch AIS API. Users can search for ferries by name and use their current positions as starting points for route calculations.

## Features

- **Live Ferry Positions**: Real-time ferry locations via Barentswatch AIS API
- **Ferry Search**: Search and select ferries by name in the route planner
- **Route Integration**: Use ferry positions as starting/ending points for sea route calculations
- **Norwegian Fleet Focus**: Covers 90+ Norwegian coastal ferries
- **Data Validation**: Ensures ferry positions are within Norwegian waters and recently updated

## Setup Instructions

### 1. API Authentication

Get a Barentswatch API token and configure it:

```bash
export BARENTSWATCH_API_TOKEN="your_actual_token_here"
```

### 2. Ferry Data Processing

Process the ferry CSV data to fetch current positions:

```bash
python scripts/process_ferries.py
```

This script will:
- Read ferry data from `data/ferries.csv`
- Fetch current positions from Barentswatch API
- Validate positions (Norwegian waters, timestamp freshness)
- Generate `data/ferries.json` with position data

### 3. Start the Application

The ferry data will be automatically loaded when the Flask app starts:

```bash
python app.py
```

## Data Flow

1. **CSV Input**: Ferry list with names, IMO numbers, and MMSI numbers (`data/ferries.csv`)
2. **Processing**: Script fetches live positions via Barentswatch API
3. **JSON Output**: Processed data saved to `data/ferries.json`
4. **Backend Loading**: Flask app loads ferry data on startup
5. **Frontend Integration**: Ferry data loaded via `/api/ferries` endpoint
6. **User Interface**: Ferries appear in search dropdown and as clickable markers

## API Endpoints

### GET /api/ferries

Returns list of ferries with current positions.

**Response format:**
```json
[
  {
    "name": "Ferry Name",
    "imo": "1234567",
    "mmsi": "257123456",
    "lat": 59.1234,
    "lon": 10.5678,
    "lastUpdate": "2026-03-25T10:00:00Z"
  }
]
```

## Data Validation

### MMSI Format
- Must be exactly 9 digits
- Range: 100000000 - 999999999

### Geographic Bounds
- Latitude: 58° - 81° N (Norwegian waters)
- Longitude: 4° - 32° E

### Timestamp Validation
- Positions older than 24 hours are rejected
- Missing timestamps are allowed (fallback behavior)

## File Structure

```
data/
├── ferries.csv          # Input: Ferry list with MMSI numbers
└── ferries.json         # Output: Processed positions (generated)

scripts/
└── process_ferries.py   # Processing script

tests/
├── test_ferry_api.py         # API endpoint tests
└── test_ferry_processing.py  # Processing function tests

templates/
└── index.html           # Frontend integration
```

## Error Handling

- **Missing API Token**: Script fails with clear error message
- **API Failures**: Individual ferry failures are logged but don't stop processing
- **Invalid Positions**: Positions outside Norwegian waters are rejected
- **Network Issues**: Requests have 10-second timeouts with retry logic

## Rate Limiting

The processing script includes:
- 0.5-second delay between API requests
- Timeout handling for API calls
- Graceful failure for individual ferries

## Testing

Run the test suite to verify integration:

```bash
# Test processing functions
python tests/test_ferry_processing.py

# Test API endpoints
python tests/test_ferry_api.py
```

## Troubleshooting

### No ferries appearing in search
1. Check that `data/ferries.json` exists
2. Verify ferry data was loaded (check startup logs)
3. Confirm `/api/ferries` endpoint returns data

### API authentication errors
1. Verify `BARENTSWATCH_API_TOKEN` environment variable is set
2. Check token validity with Barentswatch
3. Ensure token has AIS data access permissions

### Position validation failures
1. Check ferry positions are within Norwegian waters (58-81°N, 4-32°E)
2. Verify timestamps are within 24 hours
3. Review processing script logs for detailed validation errors

### Rate limiting issues
1. Increase delay between API requests in processing script
2. Process ferries in smaller batches
3. Check Barentswatch API rate limits

## Security Notes

- API token should be kept secure and not committed to version control
- Consider using environment files (.env) for token management
- Regularly rotate API tokens according to security best practices