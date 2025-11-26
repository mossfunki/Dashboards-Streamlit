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
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json

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
# ENHANCED PRODUCT DATABASE WITH ML IDENTIFICATION
# =========================

class ProductIdentifier:
    def __init__(self):
        self.common_machines = {
            'centrifuges': [
                'eppendorf 5415r', 'eppendorf 5424r', 'eppendorf 5804r', 'eppendorf 5430r',
                'beckman coulter allegra x-15r', 'beckman coulter avanti j-26 xp', 'beckman coulter optima xpn',
                'thermo scientific sorvall st 8', 'thermo scientific legend x1r', 'thermo scientific megafuge 16',
                'sigma 3-18k', 'sigma 2-16kl', 'sigma 1-14',
                'harrier 18/80', 'microstar 12', 'multifuge x3r'
            ],
            'microscopes': [
                'nikon eclipse ts2', 'nikon eclipse ti2', 'nikon eclipse 80i',
                'olympus bx53', 'olympus cx33', 'olympus ix83',
                'leica dm6 b', 'leica dm750', 'leica sp8',
                'zeiss axio observer', 'zeiss primostar', 'zeiss stemi 508'
            ],
            'analyzers': [
                'agilent 8890 gc', 'agilent 1260 hplc', 'agilent 6545 lc/ms',
                'waters acquity uplc', 'waters arc hplc', 'waters xevo tq-xs',
                'shimadzu gc-2030', 'shimadzu lc-2030', 'shimadzu irtracer-100',
                'perkinelmer clarus 580', 'perkinelmer flexar', 'perkinelmer frontier'
            ],
            'spectrometers': [
                'thermo scientific q exactive', 'thermo scientific isq ec', 'thermo scientific nicolet is5',
                'agilent 5977b gc/msd', 'agilent 4210 tape', 'agilent cary 3500',
                'bruker amazon sl', 'bruker tensor ii', 'bruker alfa ii'
            ]
        }
        
        # Build product database
        self.products = []
        for category, machines in self.common_machines.items():
            for machine in machines:
                self.products.append({
                    'name': machine,
                    'category': category,
                    'brand': machine.split()[0],
                    'model': ' '.join(machine.split()[1:])
                })
        
        # Prepare ML features
        self.vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(2, 4))
        self.product_names = [p['name'] for p in self.products]
        if self.product_names:
            self.tfidf_matrix = self.vectorizer.fit_transform(self.product_names)
    
    def identify_product(self, search_query):
        """Use ML to identify the most likely product from search query"""
        if not self.product_names:
            return None, 0.0
        
        # Transform query
        query_vec = self.vectorizer.transform([search_query.lower()])
        
        # Calculate similarities
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        
        # Get best match
        best_idx = np.argmax(similarities)
        best_similarity = similarities[best_idx]
        best_product = self.products[best_idx]
        
        return best_product, best_similarity

# =========================
# ENHANCED DATA SOURCES WITH BETTER PRICE EXTRACTION AND FILTERING
# =========================

def get_serpapi_key():
    if "SERPAPI_KEY" not in st.secrets:
        st.error("SERPAPI_KEY is missing from Streamlit secrets!")
        st.stop()
    return st.secrets["SERPAPI_KEY"]

def create_precise_query(base_query, exact_model):
    """Create precise search query with exclusions and exact matching"""
    # Clean the base query
    base_clean = re.sub(r'[^\w\s]', ' ', base_query).strip()
    
    # Build precise query with exclusions
    exclusions = ['parts', 'accessory', 'manual', 'broken', 'repair', 'for parts', 'empty']
    exact_phrase = f'"{exact_model}"' if exact_model else f'"{base_clean}"'
    
    exclusion_str = ' '.join([f'-{term}' for term in exclusions])
    precise_query = f'{exact_phrase} {exclusion_str}'.strip()
    
    return precise_query

def extract_price_robust(item):
    """Robust price extraction from multiple possible fields"""
    # Try multiple price fields in order of reliability
    price_fields = ['extracted_price', 'current_price', 'price', 'converted_price']
    
    for field in price_fields:
        price = item.get(field)
        if price is not None:
            if isinstance(price, (int, float)):
                return float(price)
            elif isinstance(price, str):
                # Clean and parse string price
                clean_price = re.sub(r'[^\d.]', '', price)
                if clean_price:
                    try:
                        return float(clean_price)
                    except ValueError:
                        continue
    
    # Fallback: extract from title using regex
    title = item.get('title', '')
    price_matches = re.findall(r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', title)
    if price_matches:
        try:
            # Take the first price found and clean it
            price_str = price_matches[0].replace(',', '')
            return float(price_str)
        except ValueError:
            pass
    
    return None

def is_relevant_listing(title, target_model, target_brand):
    """Determine if listing is relevant to our target product"""
    if not title:
        return False
    
    title_lower = title.lower()
    
    # Must contain brand
    if target_brand.lower() not in title_lower:
        return False
    
    # Must contain model number (exact match preferred)
    model_pattern = rf'\b{re.escape(target_model.lower())}\b'
    if re.search(model_pattern, title_lower):
        return True
    
    # Check for partial model matches with high confidence
    if any(term in title_lower for term in [target_model.lower(), target_model.split()[0].lower()]):
        # But exclude obvious mismatches
        exclusion_terms = ['parts', 'accessory', 'broken', 'repair', 'manual only']
        if not any(excl in title_lower for excl in exclusion_terms):
            return True
    
    return False

def fetch_ebay_sold_comprehensive(query, api_key, target_model, target_brand, pages=3):
    """Fetch sold data with precise filtering"""
    all_results = []
    precise_query = create_precise_query(query, target_model)
    
    for page in range(1, pages + 1):
        params = {
            "engine": "ebay",
            "_nkw": precise_query,
            "ebay_domain": "ebay.com",
            "show_only": "Sold",
            "page": page,
            "api_key": api_key,
        }
        try:
            r = requests.get("https://serpapi.com/search", params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            
            # Filter for relevant listings only
            relevant_items = []
            for item in data.get("organic_results", []):
                if is_relevant_listing(item.get('title'), target_model, target_brand):
                    # Extract price robustly
                    item['extracted_price'] = extract_price_robust(item)
                    relevant_items.append(item)
            
            all_results.extend(relevant_items)
            time.sleep(1)  # Rate limiting
        except Exception as e:
            st.warning(f"Failed to fetch sold page {page}: {e}")
            continue
    
    return {"organic_results": all_results}

def fetch_ebay_active(query, api_key, target_model, target_brand, pages=2):
    """Fetch active listings with precise filtering"""
    all_results = []
    precise_query = create_precise_query(query, target_model)
    
    for page in range(1, pages + 1):
        params = {
            "engine": "ebay",
            "_nkw": precise_query,
            "ebay_domain": "ebay.com",
            "page": page,
            "api_key": api_key,
        }
        try:
            r = requests.get("https://serpapi.com/search", params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            
            # Filter for relevant listings only
            relevant_items = []
            for item in data.get("organic_results", []):
                if is_relevant_listing(item.get('title'), target_model, target_brand):
                    # Extract price robustly
                    item['extracted_price'] = extract_price_robust(item)
                    relevant_items.append(item)
            
            all_results.extend(relevant_items)
            time.sleep(1)
        except Exception as e:
            st.warning(f"Failed to fetch active page {page}: {e}")
            continue
    
    return {"organic_results": all_results}

# =========================
# ENHANCED CACHING
# =========================

@st.cache_data(ttl=1800)
def cached_ebay_sold(query, api_key, target_model, target_brand):
    return fetch_ebay_sold_comprehensive(query, api_key, target_model, target_brand)

@st.cache_data(ttl=1800)
def cached_ebay_active(query, api_key, target_model, target_brand):
    return fetch_ebay_active(query, api_key, target_model, target_brand)

# =========================
# ENHANCED DATA EXTRACTION
# =========================

def extract_ebay_sold_with_metrics(raw, query, model, brand):
    """Extract sold items with enhanced metrics"""
    rows = []
    for item in raw.get("organic_results", []):
        price = item.get("extracted_price")
        
        rows.append({
            "scrape_datetime": datetime.now(timezone.utc).isoformat(),
            "source": "ebay_sold",
            "query": query,
            "model": model,
            "brand": brand,
            "title": item.get("title", ""),
            "price_raw": price,
            "condition_raw": item.get("condition"),
            "seller": item.get("source"),
            "is_sold": True,
            "is_active": False,
            "has_bids": "bid" in item.get('title', '').lower(),
        })
    return rows

def extract_ebay_active_listings(raw, query, model, brand):
    """Extract active listings"""
    rows = []
    for item in raw.get("organic_results", []):
        price = item.get("extracted_price")
        
        rows.append({
            "scrape_datetime": datetime.now(timezone.utc).isoformat(),
            "source": "ebay_active",
            "query": query,
            "model": model,
            "brand": brand,
            "title": item.get("title", ""),
            "price_raw": price,
            "condition_raw": item.get("condition"),
            "seller": item.get("source"),
            "is_sold": False,
            "is_active": True,
            "has_bids": "bid" in item.get('title', '').lower(),
        })
    return rows

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
        r["price"] = r.pop("price_raw", None)
        r["condition"] = normalize_condition(r.pop("condition_raw", None))
    return rows

# =========================
# ENHANCED PRICE ANALYSIS
# =========================

def calculate_price_distribution_metrics(prices):
    """Calculate comprehensive price distribution metrics"""
    if len(prices) < 2:
        return {}
    
    prices_array = np.array(prices)
    
    return {
        'mean': np.mean(prices_array),
        'median': np.median(prices_array),
        'std_dev': np.std(prices_array),
        'q1': np.percentile(prices_array, 25),
        'q3': np.percentile(prices_array, 75),
        'iqr': np.percentile(prices_array, 75) - np.percentile(prices_array, 25),
        'price_range': np.ptp(prices_array),
        'coefficient_variation': (np.std(prices_array) / np.mean(prices_array)) * 100 if np.mean(prices_array) > 0 else 0,
        'count': len(prices_array)
    }

def calculate_market_velocity(sold_df):
    """Calculate market velocity metrics"""
    if sold_df.empty:
        return {}
    
    total_sold = len(sold_df)
    days_represented = 30  # Conservative estimate
    
    return {
        'units_sold_per_week': (total_sold / days_represented) * 7,
        'total_sold_count': total_sold,
        'estimated_market_days': days_represented,
        'velocity_score': min(total_sold / 10, 10)
    }

# =========================
# ENHANCED VISUALIZATIONS
# =========================

def create_comparative_price_chart(sold_prices, active_prices, sold_metrics, active_metrics):
    """Create side-by-side price distribution chart"""
    if not sold_prices and not active_prices:
        return None
    
    fig = go.Figure()
    
    # Add sold prices histogram
    if sold_prices:
        fig.add_trace(go.Histogram(
            x=sold_prices,
            name='Sold Prices',
            nbinsx=15,
            opacity=0.7,
            marker_color='green',
            histnorm='probability'
        ))
    
    # Add active prices histogram
    if active_prices:
        fig.add_trace(go.Histogram(
            x=active_prices,
            name='Active Listings',
            nbinsx=15,
            opacity=0.7,
            marker_color='blue',
            histnorm='probability'
        ))
    
    # Add vertical lines for key metrics
    if sold_prices and sold_metrics:
        fig.add_vline(
            x=sold_metrics.get('median', 0),
            line_dash="dash",
            line_color="darkgreen",
            annotation_text=f"Sold Median: ${sold_metrics.get('median', 0):.0f}"
        )
    
    if active_prices and active_metrics:
        fig.add_vline(
            x=active_metrics.get('median', 0),
            line_dash="dash",
            line_color="darkblue",
            annotation_text=f"Active Median: ${active_metrics.get('median', 0):.0f}"
        )
    
    fig.update_layout(
        title='Price Distribution: Sold vs Active Listings',
        xaxis_title='Price ($)',
        yaxis_title='Probability Density',
        barmode='overlay',
        showlegend=True
    )
    
    # Adjust opacity for better visibility
    fig.update_traces(opacity=0.75)
    
    return fig

def create_price_box_plot(sold_prices, active_prices):
    """Create box plot comparison"""
    if not sold_prices and not active_prices:
        return None
    
    fig = go.Figure()
    
    if sold_prices:
        fig.add_trace(go.Box(
            y=sold_prices,
            name='Sold Prices',
            marker_color='green',
            boxpoints='outliers'
        ))
    
    if active_prices:
        fig.add_trace(go.Box(
            y=active_prices,
            name='Active Listings',
            marker_color='blue',
            boxpoints='outliers'
        ))
    
    fig.update_layout(
        title='Price Distribution Comparison',
        yaxis_title='Price ($)',
        showlegend=True
    )
    
    return fig

def create_market_gap_analysis(sold_metrics, active_metrics):
    """Create market gap analysis visualization"""
    if not sold_metrics or not active_metrics:
        return None
    
    categories = ['Median Price', 'Average Price', '25th Percentile', '75th Percentile']
    sold_values = [
        sold_metrics.get('median', 0),
        sold_metrics.get('mean', 0),
        sold_metrics.get('q1', 0),
        sold_metrics.get('q3', 0)
    ]
    active_values = [
        active_metrics.get('median', 0),
        active_metrics.get('mean', 0),
        active_metrics.get('q1', 0),
        active_metrics.get('q3', 0)
    ]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Sold',
        x=categories,
        y=sold_values,
        marker_color='green',
        text=[f'${v:,.0f}' for v in sold_values],
        textposition='auto',
    ))
    
    fig.add_trace(go.Bar(
        name='Active',
        x=categories,
        y=active_values,
        marker_color='blue',
        text=[f'${v:,.0f}' for v in active_values],
        textposition='auto',
    ))
    
    # Calculate and display premium percentages
    for i, (sold, active) in enumerate(zip(sold_values, active_values)):
        if sold > 0:
            premium_pct = ((active - sold) / sold) * 100
            fig.add_annotation(
                x=categories[i],
                y=max(active, sold) + max(active, sold) * 0.1,
                text=f"+{premium_pct:.1f}%",
                showarrow=False,
                font=dict(color="red" if premium_pct > 10 else "orange")
            )
    
    fig.update_layout(
        title='Market Price Gap Analysis',
        yaxis_title='Price ($)',
        barmode='group',
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
        
        if st.button("Clear Cache"):
            st.cache_data.clear()
            st.success("Cache cleared!")

    # Main input with ML product identification
    col1, col2 = st.columns(2)
    with col1:
        search_input = st.text_input(
            "What machine are you analyzing?",
            value="Eppendorf 5415R centrifuge",
            help="Describe the machine - we'll automatically identify the exact model"
        )
    
    with col2:
        st.markdown("### Product Identification")
        product_identifier = ProductIdentifier()
        identified_product, confidence = product_identifier.identify_product(search_input)
        
        if identified_product:
            st.success(f"**Identified**: {identified_product['name'].title()}")
            st.caption(f"Confidence: {confidence:.1%}")
            
            # Use identified product for search
            exact_model = identified_product['model']
            brand = identified_product['brand']
            precise_query = f"{brand} {exact_model}"
        else:
            st.warning("⚠️ No exact match found")
            # Fallback to user input
            exact_model = search_input
            brand = search_input.split()[0] if search_input.split() else "unknown"
            precise_query = search_input
    
    analyze_btn = st.button("🚀 Analyze Market Depth")

    if not analyze_btn:
        st.caption("Enter your equipment details and click Analyze Market Depth")
        return

    if not search_input.strip():
        st.warning("Please enter a search query")
        return

    api_key = get_serpapi_key()
    if not api_key:
        st.stop()

    # Data collection with progress
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        status_text.text("🔍 Identifying product and building precise search...")
        time.sleep(1)
        progress_bar.progress(20)

        status_text.text("📊 Fetching refined eBay sold data...")
        ebay_sold_raw = cached_ebay_sold(precise_query, api_key, exact_model, brand)
        progress_bar.progress(50)

        status_text.text("🔄 Fetching current active listings...")
        ebay_active_raw = cached_ebay_active(precise_query, api_key, exact_model, brand)
        progress_bar.progress(80)

        status_text.text("📈 Processing and analyzing market data...")
        # Extract and normalize data
        rows_ebay_sold = extract_ebay_sold_with_metrics(ebay_sold_raw, precise_query, exact_model, brand)
        rows_ebay_active = extract_ebay_active_listings(ebay_active_raw, precise_query, exact_model, brand)
        
        all_rows = normalize_rows(rows_ebay_sold + rows_ebay_active)
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
        st.warning("No relevant market data found. Try adjusting your search terms.")
        return

    # Filter to valid data for analysis
    sold_df = df[df['is_sold'] & df['price'].notna()]
    active_df = df[df['is_active'] & df['price'].notna()]
    
    sold_prices = sold_df['price'].tolist()
    active_prices = active_df['price'].tolist()

    if not sold_prices and not active_prices:
        st.warning("No valid price data found. Cannot perform market analysis.")
        return

    # Perform enhanced analysis
    sold_metrics = calculate_price_distribution_metrics(sold_prices) if sold_prices else {}
    active_metrics = calculate_price_distribution_metrics(active_prices) if active_prices else {}
    velocity_metrics = calculate_market_velocity(sold_df)

    # Display Key Insights
    st.header("🎯 Market Intelligence Dashboard")

    # Key Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if sold_metrics:
            median_sold = sold_metrics.get('median', 0)
            st.metric(
                "True Market Price (Sold Median)",
                f"${median_sold:,.0f}",
                help="Median of actual sold prices - most accurate market value"
            )
        else:
            st.metric("True Market Price", "No data")
    
    with col2:
        if active_metrics:
            median_active = active_metrics.get('median', 0)
            st.metric(
                "Current Asking Price (Active Median)",
                f"${median_active:,.0f}",
                help="Median of current active listings"
            )
        else:
            st.metric("Current Asking Price", "No data")
    
    with col3:
        if sold_metrics and active_metrics:
            premium = ((active_metrics.get('median', 0) - sold_metrics.get('median', 0)) / sold_metrics.get('median', 0)) * 100
            st.metric(
                "Market Premium",
                f"+{premium:.1f}%",
                help="Asking price premium over actual sold prices"
            )
        else:
            st.metric("Market Premium", "N/A")
    
    with col4:
        velocity = velocity_metrics.get('units_sold_per_week', 0)
        st.metric(
            "Market Velocity",
            f"{velocity:.1f}/week",
            help="Estimated units sold per week"
        )

    # Price Analysis Section
    st.subheader("💰 Price Distribution Analysis")
    
    if sold_metrics and active_metrics:
        suggested_buy = sold_metrics.get('median', 0) * 0.8  # 20% below median sold
        st.success(f"**Recommended Maximum Buy Price: ${suggested_buy:,.0f}**")
        st.caption(f"Based on 20% below median sold price of ${sold_metrics.get('median', 0):,.0f}")

    # Enhanced Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        comparative_chart = create_comparative_price_chart(sold_prices, active_prices, sold_metrics, active_metrics)
        if comparative_chart:
            st.plotly_chart(comparative_chart, use_container_width=True)
        else:
            st.info("Not enough data for comparative analysis")
    
    with col2:
        box_plot = create_price_box_plot(sold_prices, active_prices)
        if box_plot:
            st.plotly_chart(box_plot, use_container_width=True)
        else:
            st.info("Not enough data for box plot analysis")

    # Market Gap Analysis
    if sold_metrics and active_metrics:
        st.subheader("📊 Market Gap Analysis")
        gap_chart = create_market_gap_analysis(sold_metrics, active_metrics)
        if gap_chart:
            st.plotly_chart(gap_chart, use_container_width=True)

    # Market Health Indicators
    st.subheader("📈 Market Health Assessment")
    
    health_col1, health_col2, health_col3, health_col4 = st.columns(4)
    
    with health_col1:
        # Data quality
        total_listings = len(sold_prices) + len(active_prices)
        if total_listings >= 20:
            quality = "🏆 Excellent"
        elif total_listings >= 10:
            quality = "✅ Good"
        elif total_listings >= 5:
            quality = "⚠️ Limited"
        else:
            quality = "🔻 Poor"
        st.metric("Data Quality", quality)
    
    with health_col2:
        # Price stability
        if sold_metrics:
            cv = sold_metrics.get('coefficient_variation', 0)
            if cv < 15:
                stability = "🏆 High Stability"
            elif cv < 30:
                stability = "⚠️ Moderate"
            else:
                stability = "🔻 High Volatility"
            st.metric("Price Stability", stability)
        else:
            st.metric("Price Stability", "N/A")
    
    with health_col3:
        # Market efficiency
        if sold_metrics and active_metrics:
            premium = ((active_metrics.get('median', 0) - sold_metrics.get('median', 0)) / sold_metrics.get('median', 0)) * 100
            if premium < 10:
                efficiency = "🏆 Efficient"
            elif premium < 25:
                efficiency = "⚠️ Moderate"
            else:
                efficiency = "🔻 Inefficient"
            st.metric("Market Efficiency", efficiency)
        else:
            st.metric("Market Efficiency", "N/A")
    
    with health_col4:
        # Inventory health
        sold_count = len(sold_prices)
        active_count = len(active_prices)
        if active_count > 0:
            ratio = sold_count / active_count if active_count > 0 else 0
            if ratio > 2:
                health = "🔥 High Demand"
            elif ratio > 1:
                health = "↗️ Balanced"
            else:
                health = "💤 Oversupply"
            st.metric("Supply/Demand", health)
        else:
            st.metric("Supply/Demand", "N/A")

    # Raw Data with filtering
    st.subheader("📋 Filtered Market Data")
    
    # Show data quality metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Relevant Sold Listings", len(sold_prices))
    with col2:
        st.metric("Relevant Active Listings", len(active_prices))
    with col3:
        st.metric("Total Filtered", total_listings)
    
    display_cols = ["source", "is_sold", "is_active", "price", "condition", "title", "seller"]
    st.dataframe(df[display_cols], use_container_width=True)

    # Data Quality Note
    st.info(f"""
    **Analysis Notes:**
    - **ML Product ID**: {identified_product['name'].title() if identified_product else 'Manual search'}
    - **Precision Filtering**: Excluded parts/accessories/wrong models
    - **Sold Data**: {len(sold_prices)} verified sales
    - **Active Data**: {len(active_prices)} current listings
    - **Price Extraction**: Enhanced multi-field parsing with title fallback
    """)

if __name__ == "__main__":
    main()
