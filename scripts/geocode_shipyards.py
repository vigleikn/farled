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

    with open(csv_path, 'r', encoding='utf-8-sig') as file:
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
