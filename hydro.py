import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import openrouteservice
import geopandas as gpd
from shapely.geometry import LineString, Point
import folium
import branca.colormap as cm
from streamlit_folium import folium_static
import os

# Page configuration
st.set_page_config(
    page_title="Hydrogen Route Efficiency Analyzer",
    page_icon="https://www.v-soft.com/wp-content/uploads/2012/02/T3D.gif",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional CSS Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: 300;
        border-bottom: 2px solid #3498db;
        padding-bottom: 1rem;
    }
    .subtitle {
        text-align: center;
        color: #7f8c8d;
        margin-bottom: 2rem;
        font-size: 1.1rem;
    }
    .section-header {
        font-size: 1.5rem;
        color: #2c3e50;
        margin: 2rem 0 1rem 0;
        font-weight: 400;
        border-left: 4px solid #3498db;
        padding-left: 1rem;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid #e1e8ed;
        margin: 0.5rem 0;
        text-align: center;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 300;
        color: #2c3e50;
        margin: 0.5rem 0;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #7f8c8d;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.5rem;
    }
    .sidebar-section {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 8px;
        margin: 1rem 0;
        border-left: 4px solid #3498db;
    }
    .analysis-section {
        background: #f8f9fa;
        border-left: 4px solid #e74c3c;
        padding: 1.5rem;
        margin: 1.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    .success-status {
        background-color: #d4edda;
        color: #155724;
        padding: 0.75rem;
        border-radius: 6px;
        font-size: 0.9rem;
        margin: 0.5rem 0;
        border: 1px solid #c3e6cb;
    }
    .warning-status {
        background-color: #fff3cd;
        color: #856404;
        padding: 0.75rem;
        border-radius: 6px;
        font-size: 0.9rem;
        margin: 0.5rem 0;
        border: 1px solid #ffeaa7;
    }
    .info-box {
        background-color: #d1ecf1;
        color: #0c5460;
        padding: 1rem;
        border-radius: 6px;
        border: 1px solid #bee5eb;
        margin: 1rem 0;
    }
    .slider-help {
        font-size: 0.85rem;
        color: #6c757d;
        font-style: italic;
        margin-top: 0.5rem;
    }
    .api-help {
        background-color: #e8f4f8;
        border: 1px solid #b8dde7;
        border-radius: 6px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header Section
st.markdown('<div class="main-header">Hydrogen Route Efficiency Analyzer</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Find the most fuel-efficient route for your hydrogen vehicle</div>', unsafe_allow_html=True)

# API Key management
def get_api_key():
    try:
        if hasattr(st, 'secrets') and 'OPENROUTE_API_KEY' in st.secrets:
            return st.secrets['OPENROUTE_API_KEY']
    except Exception:
        pass
    return os.getenv('OPENROUTE_API_KEY')

api_key = get_api_key()

# City to coordinates mapping
CITY_COORDINATES = {
    "oakland, ca": (37.8044, -122.2711),
    "san jose, ca": (37.3382, -121.8863),
    "san francisco, ca": (37.7749, -122.4194),
    "los angeles, ca": (34.0522, -118.2437),
    "san diego, ca": (32.7157, -117.1611),
    "sacramento, ca": (38.5816, -121.4944),
    "fresno, ca": (36.7378, -119.7871),
    "portland, or": (45.5152, -122.6784),
    "seattle, wa": (47.6062, -122.3321),
    "denver, co": (39.7392, -104.9903),
    "phoenix, az": (33.4484, -112.0740),
    "las vegas, nv": (36.1699, -115.1398),
}

def geocode_city(city_name):
    """Convert city name to coordinates"""
    city_lower = city_name.strip().lower()
    return CITY_COORDINATES.get(city_lower, (37.8044, -122.2711))  # Default to Oakland

# Initialize session state for city persistence
if 'start_city' not in st.session_state:
    st.session_state.start_city = "Oakland, CA"
if 'end_city' not in st.session_state:
    st.session_state.end_city = "San Jose, CA"

# Professional Sidebar Layout - CLEANED UP
with st.sidebar:
    # Sidebar Header - SIMPLIFIED
    st.markdown("### API Configuration")
    
    if api_key:
        st.success("✓ API Key: Configured")
    else:
        st.error("⚠ API Key Required")
        st.markdown("""
        **Get free API key:**
        1. Visit [openrouteservice.org](https://openrouteservice.org)
        2. Sign up for free account
        3. Copy API key from dashboard
        """)
        api_key = st.text_input(
            "Paste API key here:",
            type="password",
            placeholder="Your API key...",
            help="Required for route analysis"
        )
    
    st.markdown("---")
    
    # Journey Details - SIMPLIFIED
    st.markdown("### Route Details")
    
    # Use session state to persist city values
    start_city = st.text_input("From City", value=st.session_state.start_city, key="start_city_input")
    end_city = st.text_input("To City", value=st.session_state.end_city, key="end_city_input")
    
    # Update session state when cities change
    if start_city != st.session_state.start_city:
        st.session_state.start_city = start_city
    if end_city != st.session_state.end_city:
        st.session_state.end_city = end_city
    
    # Geocode cities immediately
    start_lat, start_lon = geocode_city(start_city)
    end_lat, end_lon = geocode_city(end_city)
    
    # Show coordinates being used
    st.info(f"**Using coordinates:**\n- Start: {start_lat:.4f}, {start_lon:.4f}\n- End: {end_lat:.4f}, {end_lon:.4f}")
    
    st.markdown("---")
    
    # Vehicle Settings - SIMPLIFIED
    st.markdown("### ⚡ Vehicle Settings")
    
    hydrogen_efficiency = st.slider(
        "Miles per kg of hydrogen", 
        min_value=40, max_value=100, value=65,
        help="Vehicle fuel efficiency"
    )
    
    elevation_penalty = st.slider(
        "Elevation energy cost", 
        min_value=10, max_value=50, value=25,
        help="1 meter climb = extra miles of travel"
    )
    
    # Analysis Button
    analyze_button = st.button(
        " Find Most Efficient Route",
        type="primary",
        use_container_width=True
    )

# Enhanced analysis function
def analyze_routes_enhanced(api_key, start, end, start_city_name, end_city_name, hydrogen_eff=65, elev_penalty=25):
    """Enhanced function to analyze multiple route options automatically"""
    if not api_key:
        st.error("❌ API configuration required for route analysis")
        return None
    
    try:
        client = openrouteservice.Client(key=api_key)
        
        # Show the actual cities being analyzed
        st.info(f" Analyzing routes from **{start_city_name}** to **{end_city_name}**")
        st.info(f" Coordinates: ({start[1]:.4f}, {start[0]:.4f}) to ({end[1]:.4f}, {end[0]:.4f})")
        
        # Generate multiple route options
        route_options = []
        
        # Direct route (fastest)
        with st.spinner("Finding fastest route..."):
            try:
                direct_route = client.directions(
                    coordinates=[start, end],
                    profile='driving-car',
                    format='geojson',
                    validate=True,
                    instructions=False
                )
                route_options.append(("Fastest Route", direct_route))
            except Exception as e:
                st.warning(f"Could not get fastest route: {e}")
        
        # Alternative route (shorter distance)
        with st.spinner("Finding shorter route..."):
            try:
                short_route = client.directions(
                    coordinates=[start, end],
                    profile='driving-car',
                    format='geojson',
                    validate=True,
                    instructions=False,
                    options={"avoid_features": ["highways"]}
                )
                route_options.append(("Shorter Route", short_route))
            except Exception as e:
                st.warning(f"Could not get shorter route: {e}")
        
        # Alternative route 2 (scenic)
        with st.spinner("Finding alternative route..."):
            try:
                scenic_route = client.directions(
                    coordinates=[start, end],
                    profile='driving-car',
                    format='geojson',
                    validate=True,
                    instructions=False,
                    options={"avoid_features": ["highways", "tollways"]}
                )
                route_options.append(("Scenic Route", scenic_route))
            except Exception as e:
                st.warning(f"Could not get alternative route: {e}")
        
        if not route_options:
            st.error("❌ No routes could be found. Please check your cities and API key.")
            return None
        
        # Process all found routes
        all_routes = []
        all_points = []
        
        for route_name, route_data in route_options:
            geom = LineString(route_data['features'][0]['geometry']['coordinates'])
            all_routes.append({'route_id': route_name, 'geometry': geom})
        
        gdf = gpd.GeoDataFrame(all_routes, crs='EPSG:4326')
        
        # Sample points for elevation analysis
        def sample_points(line, spacing_meters=500):
            line_proj = line.to_crs(epsg=3310)
            length = line_proj.geometry.length.values[0]
            distances = np.arange(0, length, spacing_meters)
            sampled_points = [line_proj.geometry.values[0].interpolate(d) for d in distances]
            return gpd.GeoDataFrame(geometry=sampled_points, crs='EPSG:3310').to_crs(epsg=4326)
        
        for i, row in gdf.iterrows():
            sampled = sample_points(gdf.loc[[i]])
            sampled['route_id'] = row['route_id']
            all_points.append(sampled)
        
        points_gdf = gpd.GeoDataFrame(pd.concat(all_points), crs='EPSG:4326')
        
        # Get elevation data
        def get_elevation_batch(latlons):
            url = 'https://api.open-elevation.com/api/v1/lookup'
            locations = [{"latitude": lat, "longitude": lon} for lat, lon in latlons]
            try:
                response = requests.post(url, json={"locations": locations}, timeout=10)
                response.raise_for_status()
                data = response.json()
                return [pt['elevation'] for pt in data['results']]
            except Exception as e:
                st.warning(f"Elevation data issue: {str(e)}")
                return [np.nan] * len(latlons)
        
        with st.spinner("Analyzing elevation profiles..."):
            latlons = [(pt.y, pt.x) for pt in points_gdf.geometry]
            batch_size = 100
            batches = [latlons[i:i+batch_size] for i in range(0, len(latlons), batch_size)]
            
            elevations = []
            for batch in batches:
                elevations += get_elevation_batch(batch)
                time.sleep(0.3)
            
            points_gdf['elevation_m'] = elevations
        
        # Calculate elevation gain and efficiency metrics
        elevation_gain = []
        for route in points_gdf['route_id'].unique():
            route_points = points_gdf[points_gdf['route_id'] == route].sort_index()
            diff = route_points['elevation_m'].diff()
            gain = diff[diff > 0].sum()
            elevation_gain.append({'route_id': route, 'elevation_gain_m': gain})
        
        gain_df = pd.DataFrame(elevation_gain)
        
        # Calculate distances and efficiency
        gdf['distance_km'] = gdf.to_crs(epsg=3310).geometry.length / 1000
        gdf['distance_miles'] = gdf['distance_km'] * 0.621371
        
        df = gdf[['route_id', 'distance_km', 'distance_miles']].merge(gain_df, on='route_id')
        
        # Compute adjusted effective distance
        df['effective_distance_km'] = df['distance_km'] + (df['elevation_gain_m'] / (elev_penalty * 1.60934))
        df['effective_distance_miles'] = df['distance_miles'] + (df['elevation_gain_m'] / elev_penalty)
        
        # Hydrogen consumption
        df['hydrogen_kg'] = df['effective_distance_miles'] / hydrogen_eff
        df['hydrogen_per_km'] = (df['hydrogen_kg'] / df['distance_km'] * 1000)
        df['hydrogen_per_mile'] = (df['hydrogen_kg'] / df['distance_miles'] * 1000)
        
        # Calculate savings
        min_h2 = df['hydrogen_kg'].min()
        df['savings_kg'] = df['hydrogen_kg'] - min_h2
        df['savings_percent'] = ((df['hydrogen_kg'] - min_h2) / df['hydrogen_kg'] * 100).round(1)
        
        # Calculate segment grades for visualization
        def compute_segment_grades(points_df):
            segments = []
            for route in points_df['route_id'].unique():
                points = points_df[points_df['route_id'] == route].reset_index()
                for i in range(len(points) - 1):
                    p1 = points.loc[i].geometry
                    p2 = points.loc[i + 1].geometry
                    line = LineString([p1, p2])
                    
                    horiz_dist = p1.distance(p2) * 111_139
                    elev_diff = points.loc[i + 1, 'elevation_m'] - points.loc[i, 'elevation_m']
                    grade = (elev_diff / horiz_dist) * 100 if horiz_dist > 0 else 0
                    
                    segments.append({
                        'geometry': line,
                        'route_id': route,
                        'grade_pct': grade,
                        'elevation_gain': elev_diff
                    })
            
            return gpd.GeoDataFrame(segments, crs="EPSG:4326")
        
        segment_gdf = compute_segment_grades(points_gdf)
        
        return df, gdf, segment_gdf, points_gdf
        
    except Exception as e:
        st.error(f"❌ Route analysis error: {str(e)}")
        return None

# Main content area
if analyze_button and api_key:
    start_coord = [start_lon, start_lat]
    end_coord = [end_lon, end_lat]
    
    result = analyze_routes_enhanced(api_key, start_coord, end_coord, start_city, end_city, hydrogen_efficiency, elevation_penalty)
    
    if result:
        df, gdf, segment_gdf, points_gdf = result
        
        # Find the most efficient route
        best_route_row = df.loc[df['hydrogen_kg'].idxmin()]
        worst_route_row = df.loc[df['hydrogen_kg'].idxmax()]
        
        # Results Header
        st.markdown("## Route Analysis Results")
        st.markdown(f"### Recommended Route for {start_city} → {end_city}")
        
        # Highlight the best route
        st.success(f"**Best Choice:** {best_route_row['route_id']} - Only {best_route_row['hydrogen_kg']:.2f} kg hydrogen required")
        
        # Key Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            savings_kg = worst_route_row['hydrogen_kg'] - best_route_row['hydrogen_kg']
            st.metric("Fuel Savings", f"{savings_kg:.2f} kg")
        
        with col2:
            savings_percent = (savings_kg / worst_route_row['hydrogen_kg'] * 100)
            st.metric("Efficiency Gain", f"{savings_percent:.1f}%")
        
        with col3:
            st.metric("Best Distance", f"{best_route_row['distance_miles']:.1f} mi")
        
        with col4:
            elev_impact = best_route_row['effective_distance_miles'] - best_route_row['distance_miles']
            st.metric("Elevation Impact", f"+{elev_impact:.1f} mi")
        
        # Detailed Comparison
        st.markdown("### Route Comparison")
        
        display_df = df.copy()
        display_df['Distance (mi)'] = display_df['distance_miles'].round(1)
        display_df['Elevation (m)'] = display_df['elevation_gain_m'].round(0)
        display_df['Hydrogen (kg)'] = display_df['hydrogen_kg'].round(3)
        display_df['Efficiency (g/mi)'] = display_df['hydrogen_per_mile'].round(1)
        
        display_df = display_df[['route_id', 'Distance (mi)', 'Elevation (m)', 'Hydrogen (kg)', 'Efficiency (g/mi)']]
        display_df = display_df.rename(columns={'route_id': 'Route'})
        
        st.dataframe(display_df, use_container_width=True)
        
        # Visualization
        st.markdown("### Route Visualization")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Create map
            center = [points_gdf.geometry.y.mean(), points_gdf.geometry.x.mean()]
            m = folium.Map(location=center, zoom_start=10)
            
            # Color routes by efficiency
            colors = ['#27ae60', '#3498db', '#e74c3c']  # Green to red
            
            for i, (_, row) in enumerate(segment_gdf.iterrows()):
                color = colors[i % len(colors)]
                folium.PolyLine(
                    locations=[(pt[1], pt[0]) for pt in row['geometry'].coords],
                    color=color,
                    weight=4,
                    tooltip=f"{row['route_id']}",
                    opacity=0.8
                ).add_to(m)
            
            folium.Marker([start_lat, start_lon], popup="Start", tooltip="Start").add_to(m)
            folium.Marker([end_lat, end_lon], popup="End", tooltip="End").add_to(m)
            
            folium_static(m)
        
        with col2:
            # Efficiency chart
            fig, ax = plt.subplots(figsize=(8, 6))
            routes = df['route_id']
            hydrogen_kg = df['hydrogen_kg']
            
            colors = ['#27ae60' if x == min(hydrogen_kg) else '#3498db' for x in hydrogen_kg]
            
            bars = ax.bar(routes, hydrogen_kg, color=colors, alpha=0.8)
            ax.set_ylabel('Hydrogen (kg)')
            ax.set_title('Fuel Consumption')
            plt.xticks(rotation=45, ha='right')
            
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                       f'{height:.2f} kg', ha='center', va='bottom')
            
            st.pyplot(fig)

elif analyze_button and not api_key:
    st.error("Please configure your OpenRouteService API key in the sidebar.")

else:
    # Welcome Section
    st.markdown("### Welcome to the Hydrogen Route Efficiency Analyzer")
    st.markdown("""
    Find the most fuel-efficient routes for your hydrogen vehicle. Simply:
    
    1. **Enter your API key** (free from OpenRouteService)
    2. **Type your start and end cities**
    3. **Adjust vehicle settings**
    4. **Click 'Find Most Efficient Route'**
    
    **Supported cities:** Oakland, San Jose, San Francisco, Los Angeles, San Diego, 
    Sacramento, Fresno, Portland, Seattle, Denver, Phoenix, Las Vegas
    """)

# Footer
st.markdown("---")
st.markdown("*Hydrogen Route Efficiency Analyzer • Advanced Fuel Consumption Modeling*")
