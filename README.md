# Dashboards-Streamlit

Interactive data dashboards built with Streamlit. This repo contains two standalone tools: a machine market research analyzer and a hydrogen vehicle route efficiency analyzer.

---

## Dashboards

### Machine Market Analyzer (`LabMarketResearchDash.py`)

Pulls live eBay listings via SerpAPI to compare sold vs. active prices for industrial equipment. Uses TF-IDF vectorization and cosine similarity to match products, then surfaces market premium, demand signals, and price distribution metrics.

### Hydrogen Route Efficiency Analyzer (`hydro.py`)

Compares multiple driving routes (fastest, shorter, scenic) for a hydrogen vehicle trip between two cities. Fetches elevation data along each route and models fuel consumption adjusted for elevation gain, outputting a recommended route with a Folium map and bar chart.

---

## Key Features

- **Market Analyzer**
  - SerpAPI integration for real-time eBay sold/active listing data
  - ML-based product matching (TF-IDF + cosine similarity)
  - Price distribution metrics and Plotly visualizations
  - Filtered data tables with market velocity indicators

- **Hydrogen Route Analyzer**
  - OpenRouteService API for multi-route generation
  - Open-Elevation API for elevation profiling along routes
  - Configurable vehicle efficiency and elevation energy cost
  - Interactive Folium map with color-coded route overlays
  - Supports 12 preset West Coast / Southwest US cities

---

## Tech Stack

| Library | Purpose |
|---|---|
| Streamlit | App framework |
| Pandas / NumPy | Data manipulation |
| Plotly | Interactive charts |
| Matplotlib / Folium | Static charts, maps |
| scikit-learn | TF-IDF vectorization |
| SciPy | Statistical analysis |
| openrouteservice | Route data |
| GeoPandas / Shapely | Geospatial processing |
| requests | HTTP calls |

---

## Setup

```bash
# Clone the repo
git clone https://github.com/mossfunki/Dashboards-Streamlit.git
cd Dashboards-Streamlit

# Install dependencies
pip install -r requirements.txt
```

### Machine Market Analyzer

Requires a [SerpAPI](https://serpapi.com) key. Set it via Streamlit secrets or as an environment variable before running.

```bash
streamlit run LabMarketResearchDash.py
```

### Hydrogen Route Analyzer

Requires a free [OpenRouteService](https://openrouteservice.org) API key. Enter it in the sidebar on first run, or set `OPENROUTE_API_KEY` in your environment / `.streamlit/secrets.toml`.

```bash
streamlit run hydro.py
```

---

## Status

Work in progress. Both dashboards are functional but under active refinement — API error handling, additional city support, and UI polish are ongoing.
