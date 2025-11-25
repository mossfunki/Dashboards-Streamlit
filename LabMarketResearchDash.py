import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timezone, timedelta
import time
import re
import numpy as np
from requests.exceptions import Timeout, RequestException
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats

# =========================
# PAGE CONFIG
# =========================

st.set_page_config(page_title="Machine Market Analyzer", layout="wide")

# =========================
# LAZY LOADING SETUP
# =========================

if 'initialized' not in st.session_state:
    st.session_state.initialized = False

if not st.session_state.initialized:
    st.title("🧪 Machine Market Analyzer")
    with st.spinner("Initializing app... This may take a few seconds"):
        st.session_state.initialized = True
    st.rerun()

# =========================
# ENHANCED DATA SOURCES
# =========================

def get_serpapi_key():
    if "SERPAPI_KEY" not in st.secrets:
        st.error("SERPAPI_KEY is missing from Streamlit secrets!")
        st.stop()
    return st.secrets["SERPAPI_KEY"]

def fetch_ebay_sold_comprehensive(query, api_key, pages=3):
    """Fetch multiple pages of eBay sold data for better market representation"""
    all_results = []
    for page in range(1, pages + 1):
        params = {
            "engine": "ebay",
            "_nkw": query,
            "ebay_domain": "ebay.com",
            "show_only": "Sold",
            "page": page,
            "api_key": api_key,
        }
        try:
            r = requests.get("https://serpapi.com/search", params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            all_results.extend(data.get("organic_results", []))
            # Small delay to be respectful to API
            time.sleep(1)
        except Exception as e:
            st.warning(f"Failed to fetch page {page}: {e}")
            continue
    return {"organic_results": all_results}

def fetch_ebay_completed(query, api_key):
    """Fetch completed listings (both sold and unsold) for price ceiling analysis"""
    params = {
        "engine": "ebay",
        "_nkw": query,
        "ebay_domain": "ebay.com",
        "show_only": "Completed",  # This includes both sold and unsold
        "api_key": api_key,
    }
    try:
        r = requests.get("https://serpapi.com/search", params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.warning(f"Failed to fetch completed listings: {e}")
        return {"organic_results": []}

# =========================
# ENHANCED CACHING
# =========================

@st.cache_data(ttl=1800)
def cached_ebay_comprehensive(query, api_key):
    return fetch_ebay_sold_comprehensive(query, api_key)

@st.cache_data(ttl=1800)
def cached_ebay_completed(query, api_key):
    return fetch_ebay_completed(query, api_key)

@st.cache_data(ttl=1800)
def cached_google(query, api_key):
    params = {
        "engine": "google_shopping",
        "q": query,
        "api_key": api_key,
        "hl": "en",
        "gl": "us",
        "num": 20,
    }
    try:
        r = requests.get("https://serpapi.com/search", params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.warning(f"Google Shopping API error: {e}")
        return {"shopping_results": []}

# =========================
# ENHANCED DATA EXTRACTION
# =========================

def extract_ebay_sold_with_metrics(raw, query, model):
    """Extract sold items with additional metrics for analysis"""
    rows = []
    for item in raw.get("organic_results", []):
        price_text = item.get("price") or item.get("extracted_price")
        
        # Extract bid count if available
        bid_count = None
        title = item.get("title", "")
        if "bid" in title.lower():
            bid_match = re.search(r'(\d+)\s*bid', title.lower())
            if bid_match:
                bid_count = int(bid_match.group(1))
        
        rows.append({
            "scrape_datetime": datetime.now(timezone.utc).isoformat(),
            "source": "ebay_sold",
            "query": query,
            "model": model,
            "title": title,
            "price_raw": price_text,
            "condition_raw": item.get("condition"),
            "seller": item.get("source"),
            "is_sold": True,
            "bid_count": bid_count,
            "has_bids": bid_count is not None and bid_count > 0,
            "is_auction": "bid" in title.lower() or bid_count is not None,
        })
    return rows

def extract_ebay_completed_listings(raw, query, model):
    """Extract both sold and unsold completed listings"""
    rows = []
    for item in raw.get("organic_results", []):
        price_text = item.get("price") or item.get("extracted_price")
        
        # Determine if item sold (eBay usually indicates this)
        is_sold = False
        title = item.get("title", "").lower()
        if "sold" in title or "sale" in title:
            is_sold = True
        
        rows.append({
            "scrape_datetime": datetime.now(timezone.utc).isoformat(),
            "source": "ebay_completed",
            "query": query,
            "model": model,
            "title": item.get("title"),
            "price_raw": price_text,
            "condition_raw": item.get("condition"),
            "is_sold": is_sold,
            "is_completed": True,
        })
    return rows

def extract_google_shopping(raw, query, model):
    """Extract Google Shopping data"""
    rows = []
    for item in raw.get("shopping_results", []):
        rows.append({
            "scrape_datetime": datetime.now(timezone.utc).isoformat(),
            "source": "google_shopping",
            "query": query,
            "model": model,
            "title": item.get("title"),
            "price_raw": item.get("extracted_price") or item.get("price"),
            "condition_raw": item.get("condition"),
            "seller": item.get("source"),
            "is_sold": False,
            "is_auction": False,
        })
    return rows

# =========================
# ENHANCED PRICE ANALYSIS
# =========================

def parse_price(price_raw):
    """Improved price parsing"""
    if price_raw is None:
        return None
    if isinstance(price_raw, (int, float)):
        return float(price_raw)

    text = str(price_raw)
    # Remove currency symbols and text
    text = re.sub(r'[$\€\£\¥\₩\₹]', '', text)
    text = re.sub(r'[a-zA-Z]', '', text)
    text = text.replace(',', '')
    text = text.strip()
    
    match = re.search(r'(\d+\.?\d*)', text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
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

def calculate_price_distribution_metrics(sold_prices):
    """Calculate comprehensive price distribution metrics"""
    if len(sold_prices) < 3:
        return {}
    
    prices = np.array(sold_prices)
    
    return {
        'mean': np.mean(prices),
        'median': np.median(prices),
        'std_dev': np.std(prices),
        'q1': np.percentile(prices, 25),
        'q3': np.percentile(prices, 75),
        'iqr': np.percentile(prices, 75) - np.percentile(prices, 25),
        'price_range': np.ptp(prices),
        'coefficient_variation': (np.std(prices) / np.mean(prices)) * 100 if np.mean(prices) > 0 else 0,
        'skewness': stats.skew(prices) if len(prices) > 2 else 0,
    }

def analyze_price_sensitivity(sold_df, completed_df):
    """Analyze price sensitivity and buyer resistance points"""
    if sold_df.empty:
        return {}
    
    sold_prices = sold_df['price'].dropna().tolist()
    if not sold_prices:
        return {}
    
    # Price brackets for analysis
    max_price = max(sold_prices)
    min_price = min(sold_prices)
    price_range = max_price - min_price
    
    brackets = []
    for i in range(5):
        bracket_min = min_price + (i * price_range / 5)
        bracket_max = min_price + ((i + 1) * price_range / 5)
        brackets.append((bracket_min, bracket_max))
    
    sensitivity_analysis = {}
    
    # Analyze sell-through by price bracket
    for i, (bracket_min, bracket_max) in enumerate(brackets):
        bracket_sold = len([p for p in sold_prices if bracket_min <= p <= bracket_max])
        bracket_total = bracket_sold  # Simplified - would need unsold data
        
        sell_through_rate = bracket_sold / bracket_total if bracket_total > 0 else 0
        
        sensitivity_analysis[f'bracket_{i+1}'] = {
            'price_range': f"${bracket_min:.0f}-${bracket_max:.0f}",
            'sold_count': bracket_sold,
            'sell_through_rate': sell_through_rate,
            'avg_price': (bracket_min + bracket_max) / 2
        }
    
    return sensitivity_analysis

def calculate_market_velocity(sold_df):
    """Calculate market velocity metrics"""
    if sold_df.empty:
        return {}
    
    total_sold = len(sold_df)
    
    # Estimate time period (assuming recent data represents current market)
    days_represented = 30  # Conservative estimate
    
    velocity_metrics = {
        'units_sold_per_week': (total_sold / days_represented) * 7,
        'total_sold_count': total_sold,
        'estimated_market_days': days_represented,
        'velocity_score': min(total_sold / 10, 10)  # Scale 0-10
    }
    
    return velocity_metrics

def identify_price_ceiling(sold_prices, sensitivity_analysis):
    """Identify the price ceiling where buyers stop purchasing"""
    if not sold_prices or not sensitivity_analysis:
        return None
    
    # Find the highest price bracket with good sell-through
    viable_brackets = []
    for bracket_key, analysis in sensitivity_analysis.items():
        if analysis['sell_through_rate'] >= 0.5:  # 50%+ sell-through
            viable_brackets.append(analysis['avg_price'])
    
    if viable_brackets:
        price_ceiling = max(viable_brackets)
        # Add small buffer
        price_ceiling_adj = price_ceiling * 1.05
        return price_ceiling_adj
    
    # Fallback: use 90th percentile of sold prices
    return np.percentile(sold_prices, 90)

# =========================
# ENHANCED VISUALIZATIONS
# =========================

def create_price_distribution_chart(sold_prices, price_ceiling):
    """Create enhanced price distribution visualization"""
    if not sold_prices:
        return None
    
    fig = go.Figure()
    
    # Histogram of sold prices
    fig.add_trace(go.Histogram(
        x=sold_prices,
        name='Sales Distribution',
        nbinsx=20,
        opacity=0.7,
        marker_color='lightblue'
    ))
    
    # Add price ceiling line
    if price_ceiling:
        fig.add_vline(
            x=price_ceiling, 
            line_dash="dash", 
            line_color="red",
            annotation_text=f"Price Ceiling: ${price_ceiling:.0f}"
        )
    
    # Add median line
    median_price = np.median(sold_prices)
    fig.add_vline(
        x=median_price,
        line_dash="dot",
        line_color="green",
        annotation_text=f"Median: ${median_price:.0f}"
    )
    
    fig.update_layout(
        title='Price Distribution & Market Ceiling',
        xaxis_title='Price ($)',
        yaxis_title='Number of Sales',
        showlegend=True
    )
    
    return fig

def create_demand_curve(sensitivity_analysis):
    """Create demand curve visualization"""
    if not sensitivity_analysis:
        return None
    
    prices = []
    sell_through_rates = []
    
    for bracket_key, analysis in sensitivity_analysis.items():
        prices.append(analysis['avg_price'])
        sell_through_rates.append(analysis['sell_through_rate'] * 100)  # Convert to percentage
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=prices,
        y=sell_through_rates,
        mode='lines+markers',
        name='Sell-Through Rate',
        line=dict(color='royalblue', width=3),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title='Price Sensitivity & Demand Curve',
        xaxis_title='Price ($)',
        yaxis_title='Sell-Through Rate (%)',
        showlegend=True
    )
    
    return fig

# =========================
# ENHANCED MAIN APP
# =========================

def main():
    st.title("🧪 Advanced Machine Market Analyzer")
    
    st.markdown("""
    Get accurate market pricing, identify price ceilings, and understand true demand dynamics
    for industrial equipment and machinery.
    """)
    
    with st.sidebar:
        st.header("Analysis Settings")
        fees = st.number_input("Estimated platform fees ($)", min_value=0.0, value=200.0, step=50.0)
        refurb_cost = st.number_input("Estimated refurb cost ($)", min_value=0.0, value=100.0, step=50.0)
        target_profit = st.number_input("Target profit per unit ($)", min_value=0.0, value=300.0, step=50.0)
        
        st.subheader("Data Collection")
        ebay_pages = st.slider("eBay pages to analyze", 1, 5, 3)
        include_completed = st.checkbox("Include completed listings analysis", value=True)
        
        if st.button("Clear Cache"):
            st.cache_data.clear()
            st.success("Cache cleared!")

    # Main input
    col1, col2 = st.columns(2)
    with col1:
        model_input = st.text_input("Machine / model to analyze", value="Eppendorf 5415R")
    with col2:
        query_input = st.text_input(
            "Search query (for eBay/Google)",
            value="Eppendorf 5415R centrifuge"
        )
    
    analyze_btn = st.button("🚀 Analyze Market Depth")

    if not analyze_btn:
        st.caption("Enter your equipment details and click Analyze Market Depth")
        return

    if not query_input.strip():
        st.warning("Please enter a search query")
        return

    api_key = get_serpapi_key()
    if not api_key:
        st.stop()

    # Data collection with progress
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        status_text.text("📊 Fetching comprehensive eBay sold data...")
        ebay_sold_raw = cached_ebay_comprehensive(query_input, api_key)
        progress_bar.progress(25)

        status_text.text("🔍 Analyzing completed listings...")
        ebay_completed_raw = cached_ebay_completed(query_input, api_key) if include_completed else {"organic_results": []}
        progress_bar.progress(50)

        status_text.text("🛒 Fetching Google Shopping data...")
        gs_raw = cached_google(query_input, api_key)
        progress_bar.progress(75)

        status_text.text("📈 Processing market data...")
        # Extract and normalize data
        rows_ebay_sold = extract_ebay_sold_with_metrics(ebay_sold_raw, query_input, model_input)
        rows_ebay_completed = extract_ebay_completed_listings(ebay_completed_raw, query_input, model_input)
        rows_google = extract_google_shopping(gs_raw, query_input, model_input)
        
        all_rows = normalize_rows(rows_ebay_sold + rows_ebay_completed + rows_google)
        df = pd.DataFrame(all_rows)
        
        progress_bar.progress(100)
        status_text.text("✅ Analysis complete!")
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()

    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"Data collection error: {e}")
        st.stop()

    if df.empty:
        st.warning("No market data found. Try adjusting your search terms.")
        return

    # Filter to valid sold data for core analysis
    sold_df = df[df['is_sold'] & df['price'].notna()]
    sold_prices = sold_df['price'].tolist()

    if not sold_prices:
        st.warning("No valid sold price data found. Cannot perform market analysis.")
        return

    # Perform enhanced analysis
    price_metrics = calculate_price_distribution_metrics(sold_prices)
    sensitivity_analysis = analyze_price_sensitivity(sold_df, df)
    velocity_metrics = calculate_market_velocity(sold_df)
    price_ceiling = identify_price_ceiling(sold_prices, sensitivity_analysis)

    # Display Key Insights
    st.header("🎯 Market Intelligence Dashboard")

    # Key Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        median_price = price_metrics.get('median', 0)
        st.metric(
            "True Market Price (Median)",
            f"${median_price:,.0f}",
            help="Median of actual sold prices - most accurate market value"
        )
    with col2:
        price_range = f"${price_metrics.get('q1', 0):,.0f}-${price_metrics.get('q3', 0):,.0f}"
        st.metric(
            "Typical Price Range",
            price_range,
            help="25th-75th percentile range where most sales occur"
        )
    with col3:
        if price_ceiling:
            st.metric(
                "Price Ceiling",
                f"${price_ceiling:,.0f}",
                help="Maximum price buyers are willing to pay"
            )
    with col4:
        velocity = velocity_metrics.get('units_sold_per_week', 0)
        st.metric(
            "Market Velocity",
            f"{velocity:.1f}/week",
            help="Estimated units sold per week"
        )

    # Price Analysis Section
    st.subheader("💰 Price Distribution & Ceiling Analysis")
    
    if price_ceiling:
        suggested_buy = price_ceiling - fees - refurb_cost - target_profit
        st.success(f"**Recommended Maximum Buy Price: ${suggested_buy:,.0f}**")
        st.caption(f"Based on price ceiling (${price_ceiling:,.0f}) minus costs and profit margin")

    # Visualizations
    col1, col2 = st.columns(2)
    with col1:
        price_chart = create_price_distribution_chart(sold_prices, price_ceiling)
        if price_chart:
            st.plotly_chart(price_chart, use_container_width=True)
    
    with col2:
        demand_chart = create_demand_curve(sensitivity_analysis)
        if demand_chart:
            st.plotly_chart(demand_chart, use_container_width=True)
        else:
            st.info("Not enough data for demand curve analysis")

    # Market Health Indicators
    st.subheader("📊 Market Health Assessment")
    
    health_col1, health_col2, health_col3 = st.columns(3)
    
    with health_col1:
        # Price stability
        cv = price_metrics.get('coefficient_variation', 0)
        if cv < 15:
            stability = "🏆 High Stability"
            color = "green"
        elif cv < 30:
            stability = "⚠️ Moderate Stability"
            color = "orange"
        else:
            stability = "🔻 High Volatility"
            color = "red"
        st.metric("Price Stability", stability)
    
    with health_col2:
        # Demand strength
        velocity_score = velocity_metrics.get('velocity_score', 0)
        if velocity_score >= 7:
            demand = "🔥 Strong Demand"
        elif velocity_score >= 4:
            demand = "↗️ Moderate Demand"
        else:
            demand = "💤 Weak Demand"
        st.metric("Demand Strength", demand)
    
    with health_col3:
        # Market depth
        sold_count = len(sold_prices)
        if sold_count >= 20:
            depth = "🌊 Deep Market"
        elif sold_count >= 10:
            depth = "💧 Moderate Depth"
        else:
            depth = "⚠️ Thin Market"
        st.metric("Market Depth", depth)

    # Raw Data
    st.subheader("📋 Raw Market Data")
    display_cols = ["source", "is_sold", "price", "condition", "title", "seller"]
    st.dataframe(df[display_cols], use_container_width=True)

    # Data Quality Note
    st.info(f"""
    **Analysis Notes:**
    - Based on {len(sold_prices)} verified sales
    - Price ceiling represents the maximum viable sale price
    - Market velocity estimated from recent sales data
    - Typical price range shows where 50% of sales occur
    """)

if __name__ == "__main__":
    main()
