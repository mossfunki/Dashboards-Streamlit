import os
import time
from datetime import datetime, timezone

import requests
import pandas as pd
import streamlit as st
from requests.exceptions import Timeout, RequestException

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
# IMPROVED SERPAPI FETCH FUNCTIONS
# =========================

def fetch_google_shopping(query, api_key, num=10, max_retries=2):
    params = {
        "engine": "google_shopping",
        "q": query,
        "api_key": api_key,
        "hl": "en",
        "gl": "us",
        "num": num,
    }
    
    for attempt in range(max_retries + 1):
        try:
            r = requests.get("https://serpapi.com/search", params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except Timeout:
            if attempt < max_retries:
                st.warning(f"Google Shopping API timeout, retrying... ({attempt + 1}/{max_retries})")
                time.sleep(2)
            else:
                st.error("Google Shopping API timeout after retries")
                return {"shopping_results": []}
        except RequestException as e:
            st.error(f"Google Shopping API error: {e}")
            return {"shopping_results": []}

def fetch_ebay_sold(query, api_key, num=20, page=1, max_retries=2):
    params = {
        "engine": "ebay",
        "_nkw": query,
        "ebay_domain": "ebay.com",
        "show_only": "Sold",
        "page": page,
        "api_key": api_key,
    }
    
    for attempt in range(max_retries + 1):
        try:
            r = requests.get("https://serpapi.com/search", params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except Timeout:
            if attempt < max_retries:
                st.warning(f"eBay API timeout, retrying... ({attempt + 1}/{max_retries})")
                time.sleep(2)
            else:
                st.error("eBay API timeout after retries")
                return {"organic_results": []}
        except RequestException as e:
            st.error(f"eBay API error: {e}")
            return {"organic_results": []}

# =========================
# IMPROVED CACHING WITH SHORTER TTL
# =========================

@st.cache_data(ttl=1800)  # 30 minutes instead of 1 hour
def cached_google(query, api_key):
    return fetch_google_shopping(query, api_key)

@st.cache_data(ttl=1800)
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
            "currency": "USD",
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

    # Demand label
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
    insights["demand_score"] = sold_count

    # Velocity
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
# IMPROVED MAIN APP
# =========================

def main():
    st.title("🧪 Machine Market Analyzer")

    st.markdown(
        "Type a machine / model name and I'll fetch recent listings + sold data, "
        "then estimate market price, demand, velocity, and a suggested max buy price."
    )

    with st.sidebar:
        st.header("Settings")
        fees = st.number_input("Estimated platform fees ($)", min_value=0.0, value=200.0, step=50.0)
        refurb_cost = st.number_input("Estimated refurb cost ($)", min_value=0.0, value=100.0, step=50.0)
        target_profit = st.number_input("Target profit per unit ($)", min_value=0.0, value=300.0, step=50.0)
        min_sold_for_demand = st.number_input("Min sold for 'Medium' demand", min_value=1, value=3, step=1)
        
        # Add a cache control option
        if st.button("Clear Cache"):
            st.cache_data.clear()
            st.success("Cache cleared!")

    model_input = st.text_input("Machine / model to analyze", value="Eppendorf 5415R")
    query_input = st.text_input(
        "Search query (used for Google/eBay; you can tweak it)",
        value="Eppendorf 5415R centrifuge"
    )

    analyze_btn = st.button("Analyze market")

    if not analyze_btn:
        st.caption("Set your parameters and click **Analyze market** to fetch data.")
        return

    # Input validation
    if not query_input.strip():
        st.warning("Please enter a search query")
        return

    api_key = get_serpapi_key()
    if not api_key:
        st.stop()

    # Use progress bars for better UX
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        status_text.text("Fetching Google Shopping data...")
        gs_raw = cached_google(query_input, api_key)
        progress_bar.progress(33)

        status_text.text("Fetching eBay sold data...")
        ebay_raw = cached_ebay(query_input, api_key)
        progress_bar.progress(66)

        status_text.text("Processing data...")
        rows_gs = extract_from_google_shopping(gs_raw, query_input, model_input)
        rows_ebay = extract_from_ebay_sold(ebay_raw, query_input, model_input)
        all_rows = normalize_rows(rows_gs + rows_ebay)

        df = pd.DataFrame(all_rows)
        progress_bar.progress(100)
        status_text.text("Complete!")
        
        # Small delay to show completion
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()

    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"Unexpected error: {e}")
        st.stop()

    if df.empty:
        st.warning("No data found for this query. Try adjusting the search term.")
        return

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

    st.subheader("Price distribution (sold vs active)")
    chart_df = df[df["price"].notna()].copy()
    if not chart_df.empty:
        chart_df["type"] = chart_df["is_sold"].map({True: "Sold", False: "Active"})
        st.bar_chart(chart_df.groupby("type")["price"].mean())

    st.subheader("Raw listings")
    display_cols = ["source", "is_sold", "price", "condition", "title", "seller", "url"]
    st.dataframe(df[display_cols])


if __name__ == "__main__":
    main()
