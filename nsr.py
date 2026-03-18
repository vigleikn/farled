"""
Henter ferje- og hurtigbåtkaier fra Entur Journey Planner API.
Filtrerer på transportMode = water (hurtigbåt/ferje).
"""

import json
import os
from pathlib import Path
import requests

CACHE_FILE = Path(__file__).parent / "data" / "quays_cache.json"

# Entur Journey Planner GraphQL (offentlig API, ingen nøkkel nødvendig)
JIT_URL = "https://api.entur.io/journey-planner/v3/graphql"

# Hele Norge bounding box
GRAPHQL_QUERY = """
{
  stopPlacesByBbox(
    minimumLatitude: 57
    maximumLatitude: 72
    minimumLongitude: 2
    maximumLongitude: 35
  ) {
    id
    name
    latitude
    longitude
    transportMode
  }
}
"""


def fetch_quays(use_cache: bool = True) -> list[dict]:
    """
    Returnerer liste over ferje-/hurtigbåt-kaier.
    Struktur per kai:
    {
        'id': str,
        'name': str,
        'stop_name': str,
        'lat': float,
        'lon': float,
        'stop_id': str,
    }
    """
    if use_cache and CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            data = json.load(f)
        print(f"Bruker cachet kai-data ({len(data)} kaier)")
        return data

    print("Henter ferje-/hurtigbåt-kaier fra Entur Journey Planner...")
    headers = {
        "ET-Client-Name": "sjovei-poc",
        "Content-Type": "application/json",
    }
    resp = requests.post(
        JIT_URL,
        json={"query": GRAPHQL_QUERY},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()

    all_stops = result.get("data", {}).get("stopPlacesByBbox", []) or []

    # Filtrer på transportMode = water (hurtigbåt / ferje)
    water_stops = []
    for stop in all_stops:
        modes = stop.get("transportMode") or []
        if isinstance(modes, str):
            modes = [modes]
        if "water" in modes:
            lat = stop.get("latitude")
            lon = stop.get("longitude")
            name = stop.get("name", "Ukjent kai")
            stop_id = stop.get("id", "")
            if lat and lon:
                water_stops.append({
                    "id": stop_id,
                    "name": name,
                    "stop_name": name,
                    "lat": lat,
                    "lon": lon,
                    "stop_id": stop_id,
                })

    # Lagre cache
    CACHE_FILE.parent.mkdir(exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(water_stops, f, ensure_ascii=False, indent=2)

    print(f"Hentet {len(water_stops)} ferje-/hurtigbåt-kaier")
    return water_stops


def get_quays_dict(use_cache: bool = True) -> dict[str, dict]:
    """Returnerer dict {quay_id: quay_info}"""
    quays = fetch_quays(use_cache=use_cache)
    return {q["id"]: q for q in quays}


if __name__ == "__main__":
    quays = fetch_quays(use_cache=False)
    print(f"\nEksempel kaier:")
    for q in quays[:10]:
        print(f"  {q['id']}: {q['name']} ({q['lat']:.4f}, {q['lon']:.4f})")
