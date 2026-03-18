# Sjøvei — Farled-kalkulator for Norge

Beregner faktisk sjøvei mellom norske kaier langs offisielle farleder (Kystverket).

## Demo

Velg to kaier, søk på adresse eller pin i kart → kart vises med rute og distanse i nautiske mil.

## Oppsett

### 1. Installer avhengigheter

```bash
pip install -r requirements.txt
```

### 2. Last ned farled-data

Last ned **Hovedled og Biled** som GeoJSON fra [Geonorge](https://kartkatalog.geonorge.no) og lagre som `data/farled.geojson`.

Alternativt — kjør nedlastingsskriptet:

```bash
python download_farled.py
```

### 3. Start serveren

```bash
python app.py
```

Åpne [http://localhost:5001](http://localhost:5001) i nettleseren.

## Datakilder

| Data | Kilde | Lisens |
|---|---|---|
| Farled senterlinjer | [Kystverket / Geonorge](https://kartkatalog.geonorge.no) | NLOD |
| Kaier og stoppesteder | [Entur NSR](https://developer.entur.org/pages-nsr-nsr/) | Åpent |
| Adressesøk | [Kartverket Adresse-API](https://ws.geonorge.no/adresser/v1/) | NLOD |

## Teknisk stack

- **Backend:** Python / Flask, GeoPandas, NetworkX, Shapely, pyproj
- **Frontend:** Leaflet.js, Vanilla JS/HTML
- **Ruting:** Dijkstra på graf bygget fra farled-senterlinjer

## Begrensninger

- Basert på Kystverkets offisielle farleder — dekker ikke alle private kaier
- Topologiske hull i farled-dataene kan gi manglende ruter på noen strekninger
- NSR dekker kun offentlige kollektivknutepunkt (kaier/terminaler)
