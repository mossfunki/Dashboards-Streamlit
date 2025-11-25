import os
import re
from datetime import datetime, timezone

import requests
import pandas as pd
import streamlit as st

# =========================
# PAGE CONFIG
# =========================

st.set_page_config(page_title="Machine Market Analyzer", layout="wide")

# =========================
# CONFIG / SECRETS
# =========================

def get_serpapi_key():
    if "SERPAPI_KEY" not in st.secrets:
        st.error("SERPAPI_KEY is missing from Streamlit secrets!")
        st.stop()
    return st.secrets["SERPAPI_KEY"]

# =========================
# SERPAPI FETCH FUNCTIONS
# =========================

def fetch_google_shopping(query, api_key, num=10):
    params = {
        "engine": "google_shopping",
        "q": query,
        "api_key": api_key,
        "hl": "en",
        "gl": "us",
        "num": num,
    }
    r = requests.get("https://serpapi.com/search", params=params)
    r.raise_for_status()
    return r.json()

def fetch_ebay_sold(query, api_key, num=20, page=1):
    """
    Fetch sold items from eBay via SerpAPI.
    """
    params = {
        "engine": "ebay",
        "_nkw": query,          # eBay search term
        "ebay_domain": "ebay.com",
        "show_only": "Sold",    # only sold listings
        "page": page,
        "api_key": api_key,
    }
    r = requests.get("https://serpapi.com/search", params=params)
    r.raise_for_status()
    return r.json()

# =========================
# CACHING WRAPPERS
# =========================

@st.cache_data(ttl=3600)  # cache results for 1 hour
def cached_google(query, api_key):
    return fetch_google_shopping(query, api_key)

@st.cache_data(ttl=3600)
def cached_ebay(query, api_key):
    return fetch_ebay_sold(query, api_key)

# =========================
# EXTRACT FUNCTIONS
# =========================

def extract_from_google_shopping(raw, query, model):
    rows = []
    for item in raw.get("shopping_results", []):
        rows.append({
            "scrape_datetime": datetime.now(timezone.utc).isoformat(),
            "source": "google_shopping",
            "query": query,
            "model": model,
            "title": item.get("title"),
            "price_raw": item.get("extracted_price") or item.get("price"),
            "currency": "USD",  # assume US for now
            "condition_raw": item.get("condition"),
            "url": item.get("link"),
            "seller": item.get("source"),
            "marketplace": "google_shopping",
            "is_sold": False,
            "location": None,
        })
    return rows

def extract_from_ebay_sold(raw, query, model):
    rows = []
    for item in raw.get("organic_results", []):
        price_text = item.get("price")
        rows.append({
            "scrape_datetime": datetime.now(timezone.utc).isoformat(),
            "source": "ebay_sold",
            "query": query,
            "model": model,
            "title": item.get("title"),
            "price_raw": price_text,
            "currency": "USD",
            "condition_raw": item.get("condition"),
            "url": item.get("link"),
            "seller": item.get("source"),
            "marketplace": "ebay",
            "is_sold": True,
            "location": item.get("location"),
        })
    return rows

# =========================
# NORMALIZATION HELPERS
# =========================

def parse_price(price_raw):
    if price_raw is None:
        return None
    if isinstance(price_raw, (int, float)):
        return float(price_raw)

    text = str(price_raw)
    # examples: "$1,250.00", "US $800.00", "$1,550"
    for ch in ["$", "€", "£", ","]:
        text = text.replace(ch, "")
    text = text.strip().split()[0]
    try:
        return float(text)
    except ValueError:
        return None

def normalize_condition(cond_raw):
    if not cond_raw:
        return "unknown"
    c = str(cond_raw).lower()
    if "new" in c:
        return "new"
    if "refurb" in c:
        return "refurbished"
    if "used" in c or "pre-owned" in c:
        return "used"
    return "unknown"

def normalize_rows(rows):
    for r in rows:
        r["price"] = parse_price(r.pop("price_raw", None))
        r["condition"] = normalize_condition(r.pop("condition_raw", None))
    return rows

# =========================
# METRICS / ANALYTICS
# =========================

def compute_insights(df, min_sold_for_demand=3):
    """
    Returns a dict of high-level insights including demand + velocity.
    """
    if df.empty:
        return {}

    sold = df[df["is_sold"] & df["price"].notna()]
    active = df[~df["is_sold"] & df["price"].notna()]

    insights = {}

    # Price stats (sold listings only)
    if not sold.empty:
        insights["sold_count"] = len(sold)
        insights["avg_sold_price"] = sold["price"].mean()
        insights["median_sold_price"] = sold["price"].median()
        insights["min_sold_price"] = sold["price"].min()
        insights["max_sold_price"] = sold["price"].max()
    else:
        insights["sold_count"] = 0
        insights["avg_sold_price"] = None
        insights["median_sold_price"] = None
        insights["min_sold_price"] = None
        insights["max_sold_price"] = None

    # Active listings stats
    if not active.empty:
        insights["active_count"] = len(active)
        insights["avg_active_price"] = active["price"].mean()
    else:
        insights["active_count"] = 0
        insights["avg_active_price"] = None

    # Demand label (simple)
    sold_count = insights["sold_count"]
    if sold_count == 0:
        demand_label = "Very low / unknown"
    elif sold_count < min_sold_for_demand:
        demand_label = "Low"
    elif sold_count < 10:
        demand_label = "Medium"
    else:
        demand_label = "High"

    insights["demand_label"] = demand_label
    insights["demand_score"] = sold_count  # raw count as simple score

    # Velocity / "time on market" style signal
    total_with_price = insights["sold_count"] + insights["active_count"]
    if total_with_price > 0:
        sell_through_rate = insights["sold_count"] / total_with_price
    else:
        sell_through_rate = 0.0

    if sell_through_rate == 0:
        velocity_label = "Unknown / very slow"
    elif sell_through_rate < 0.25:
        velocity_label = "Slow"
    elif sell_through_rate < 0.75:
        velocity_label = "Normal"
    else:
        velocity_label = "Fast"

    insights["sell_through_rate"] = sell_through_rate
    insights["velocity_label"] = velocity_label

    return insights

def suggested_buy_price(median_sold_price, fees, refurb_cost, target_profit):
    if median_sold_price is None:
        return None
    return median_sold_price - fees - refurb_cost - target_profit

# =========================
# HISTORY / DEPRECIATION
# =========================

def model_to_slug(model: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", model).strip("_").lower()
    return slug or "model"

def append_to_history(df: pd.DataFrame, model: str) -> str:
    os.makedirs("data/history", exist_ok=True)

    slug = model_to_slug(model)
    path = f"data/history/{slug}.csv"

    to_save = df.copy()

    if os.path.exists(path):
        old = pd.read_csv(path)
        combined = pd.concat([old, to_save], ignore_index=True)
    else:
        combined = to_save

    combined.to_csv(path, index=False)
    return path

def load_depreciation_series(model: str) -> pd.DataFrame:
    slug = model_to_slug(model)
    path = f"data/history/{slug}.csv"
    if not os.path.exists(path):
        return pd.DataFrame()

    hist = pd.read_csv(path)

    if "price" not in hist.columns or "is_sold" not in hist.columns:
        return pd.DataFrame()

    hist = hist[hist["is_sold"] & hist["price"].notna()].copy()
    if hist.empty:
        return hist

    if "sold_date" in hist.columns and hist["sold_date"].notna().any():
        hist["trade_date"] = pd.to_datetime(
            hist["sold_date"].fillna(hist["scrape_datetime"])
        )
    else:
        hist["trade_date"] = pd.to_datetime(hist["scrape_datetime"])

    hist["trade_date"] = hist["trade_date"].dt.date
    series = (
        hist.groupby("trade_date")["price"]
        .median()
        .reset_index()
        .sort_values("trade_date")
    )
    return series

# =========================
# MAIN APP
# =========================

def main():
    st.title("🧪 Machine Market Analyzer")

    st.markdown(
        "Type a machine / model name and I’ll fetch recent listings + sold data, "
        "then estimate market price, demand, velocity, and a suggested max buy price."
    )

# Save this run to history + show depreciation
    history_path = append_to_history(df, model_input)
    trend_df = load_depreciation_series(model_input)
    
    with st.sidebar:
        st.header("Settings")
        fees = st.number_input("Estimated platform fees ($)", min_value=0.0, value=200.0, step=50.0)
        refurb_cost = st.number_input("Estimated refurb cost ($)", min_value=0.0, value=100.0, step=50.0)
        target_profit = st.number_input("Target profit per unit ($)", min_value=0.0, value=300.0, step=50.0)
        min_sold_for_demand = st.number_input("Min sold for 'Medium' demand", min_value=1, value=3, step=1)

    model_input = st.text_input("Machine / model to analyze", value="Eppendorf 5415R")
    query_input = st.text_input(
        "Search query (used for Google/eBay; you can tweak it)",
        value="Eppendorf 5415R centrifuge"
    )

    analyze_btn = st.button("Analyze market")

    if not analyze_btn:
        st.caption("Set your parameters and click **Analyze market** to fetch data.")
        return

    api_key = get_serpapi_key()
    if not api_key:
        st.stop()

    with st.spinner("Fetching and analyzing data..."):
        try:
            gs_raw = cached_google(query_input, api_key)
            ebay_raw = cached_ebay(query_input, api_key)

            rows_gs = extract_from_google_shopping(gs_raw, query_input, model_input)
            rows_ebay = extract_from_ebay_sold(ebay_raw, query_input, model_input)
            all_rows = normalize_rows(rows_gs + rows_ebay)

            df = pd.DataFrame(all_rows)
        except requests.HTTPError as e:
            st.error(f"HTTP error: {e}")
            st.stop()
        except Exception as e:
            st.error(f"Unexpected error: {e}")
            st.stop()

    if df.empty:
        st.warning("No data found for this query. Try adjusting the search term.")
        return

    # High-level insights
    insights = compute_insights(df, min_sold_for_demand=min_sold_for_demand)

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Sold listings (sample)", insights.get("sold_count", 0))
    with col2:
        median_price = insights.get("median_sold_price")
        st.metric(
            "Median sold price",
            f"${median_price:,.0f}" if median_price else "N/A",
        )
    with col3:
        st.metric("Active listings (sample)", insights.get("active_count", 0))
    with col4:
        st.metric("Demand", insights.get("demand_label", "Unknown"))
    with col5:
        st.metric("Market velocity", insights.get("velocity_label", "Unknown"))

    st.caption(
        "Velocity is based on the ratio of sold vs active listings in this sample. "
        "Higher sell-through usually means items don't sit long on the market."
    )

    # Suggested max buy price
    suggested = suggested_buy_price(
        insights.get("median_sold_price"),
        fees=fees,
        refurb_cost=refurb_cost,
        target_profit=target_profit,
    )

    st.subheader("Suggested max buy price")
    if suggested is None:
        st.info("Not enough sold data to suggest a buy price.")
    else:
        st.success(f"Suggested max buy price: **${suggested:,.0f}**")

    st.subheader("Depreciation trend (median sold price over time)")
    if trend_df.empty or len(trend_df) < 2:
        st.info(
            "Not enough historical data yet to show a depreciation trend. "
            "Keep using this tool over time and the chart will fill in."
        )
    else:
        trend_df = trend_df.set_index("trade_date")
        st.line_chart(trend_df["price"])

    # Charts
    st.subheader("Price distribution (sold vs active)")
    chart_df = df[df["price"].notna()].copy()
    if not chart_df.empty:
        chart_df["type"] = chart_df["is_sold"].map({True: "Sold", False: "Active"})
        st.bar_chart(chart_df.groupby("type")["price"].mean())

    # Detailed table
    st.subheader("Raw listings")
    display_cols = ["source", "is_sold", "price", "condition", "title", "seller", "url"]
    st.dataframe(df[display_cols])


if __name__ == "__main__":
    main()

