import streamlit as st

# =========================
# PAGE CONFIG (at the top, lightweight)
# =========================

st.set_page_config(page_title="Machine Market Analyzer", layout="wide")

# =========================
# LAZY LOADING SETUP
# =========================

# Initialize session state for tracking if heavy imports are done
if 'initialized' not in st.session_state:
    st.session_state.initialized = False
    st.session_state.heavy_imports_done = False

# Show immediate loading message
if not st.session_state.initialized:
    st.title("🧪 Machine Market Analyzer")
    with st.spinner("Initializing app... This may take a few seconds"):
        # Load heavy imports only when needed
        import os
        import time
        from datetime import datetime, timezone
        import requests
        import pandas as pd
        from requests.exceptions import Timeout, RequestException
        
        st.session_state.heavy_imports_done = True
        st.session_state.initialized = True
        
    # Use experimental_rerun to refresh the page after imports
    st.rerun()

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

def fetch_google_shopping(query, api_key, num=10, max_retries=2):
    import requests
    from requests.exceptions import Timeout, RequestException
    
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
    import requests
    from requests.exceptions import Timeout, RequestException
    
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
# CACHING WRAPPERS
# =========================

@st.cache_data(ttl=1800)
def cached_google(query, api_key):
