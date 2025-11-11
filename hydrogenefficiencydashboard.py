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

st.set_page_config(
    page_title="Hydrogen Route Efficiency Analyzer",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.markdown("""
<style>
    .meta-tags {
        display: none !important;
    }
</style>

<div class="meta-tags">
    <!-- Open Graph Meta Tags -->
    <meta property="og:title" content="Hydrogen Route Efficiency Analyzer">
    <meta property="og:description" content="Advanced route optimization for hydrogen vehicle energy consumption analysis">
    <meta property="og:image" content="https://your-domain.com/route-analyzer-preview.png">
    <meta property="og:url" content="https://your-streamlit-app-url.streamlit.app">
    <meta property="og:type" content="website">
    
    <!-- Twitter Card Meta Tags -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="Hydrogen Route Efficiency Analyzer">
    <meta name="twitter:description" content="Advanced route optimization for hydrogen vehicle energy consumption analysis">
    <meta name="twitter:image" content="https://your-domain.com/route-analyzer-preview.png">
</div>
""", unsafe_allow_html=True)

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
    
    /* FIXED: Proper box headers */
    .section-container {
        border: 1px solid #e1e8ed;
        border-radius: 8px;
        margin: 1.5rem 0;
        background: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .section-header {
        background: #f8f9fa;
        padding: 1rem 1.5rem;
        margin: 0;
        font-size: 1.3rem;
        color: #2c3e50;
        font-weight: 500;
        border-bottom: 1px solid #e1e8ed;
        border-radius: 8px 8px 0 0;
    }
    
    .section-content {
        padding: 1.5rem;
    }
    
    /* Nested sections for hierarchy */
    .nested-container {
        border: 1px solid #e1e8ed;
        border-radius: 6px;
        margin: 1rem 0;
        background: white;
    }
    
    .nested-header {
        background: #f8f9fa;
        padding: 0.75rem 1rem;
        margin: 0;
        font-size: 1.1rem;
        color: #2c3e50;
        font-weight: 500;
        border-bottom: 1px solid #e1e8ed;
    }
    
    .nested-content {
        padding: 1rem;
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
    
    .success-status {
        background-color: #d4edda;
        color: #155724;
        padding: 0.75rem;
        border-radius: 6px;
        font-size: 0.9rem;
        margin: 0.5rem 0;
        border: 1px solid #c3e6cb;
    }
    
    .divider {
        border-top: 1px solid #ecf0f1;
        margin: 1.5rem 0;
    }  
</style>
""", unsafe_allow_html=True)

# Header Section
st.markdown('<div class="main-header">Hydrogen Route Efficiency Analyzer</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Advanced route optimization for hydrogen vehicle energy consumption analysis</div>', unsafe_allow_html=True)

# API Key management
def get_api_key():
    try:
        if hasattr(st, 'secrets') and 'OPENROUTE_API_KEY' in st.secrets:
            return st.secrets['OPENROUTE_API_KEY']
    except Exception:
        pass
    return os.getenv('OPENROUTE_API_KEY')

api_key = get_api_key()

# Professional Sidebar Layout
with st.sidebar:
    # Sidebar Header
    st.markdown("""
    <div style='text-align: center; margin-bottom: 2rem;'>
        <h2 style='color: #2c3e50; margin-bottom: 0.5rem;'>Configuration Panel</h2>
        <div style='color: #7f8c8d; font-size: 0.9rem;'>Route Analysis Parameters</div>
    </div>
    """, unsafe_allow_html=True)
    
    # API Configuration Section
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("### API Configuration")
    
    if api_key:
        st.markdown('<div class="success-status">✓ API Key: Securely Configured</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="warning-status">⚠ API Key: Required for Routing Data</div>', unsafe_allow_html=True)
        api_key = st.text_input("OpenRouteService API Key", type="password", label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Route Parameters Section
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("### Route Parameters")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Origin Coordinates**")
        start_lat = st.number_input("Latitude", value=37.8044, format="%.6f", key="start_lat")
        start_lon = st.number_input("Longitude", value=-122.2711, format="%.6f", key="start_lon")
    
    with col2:
        st.markdown("**Destination Coordinates**")
        end_lat = st.number_input("Latitude", value=37.3382, format="%.6f", key="end_lat")
        end_lon = st.number_input("Longitude", value=-121.8863, format="%.6f", key="end_lon")
    
    st.markdown("**Alternative Route Waypoints**")
    col3, col4 = st.columns(2)
    with col3:
        via1_lat = st.number_input("Route 2 Latitude", value=37.5297, format="%.6f")
        via1_lon = st.number_input("Route 2 Longitude", value=-121.9189, format="%.6f")
    
    with col4:
        via2_lat = st.number_input("Route 3 Latitude", value=37.5010, format="%.6f")
        via2_lon = st.number_input("Route 3 Longitude", value=-122.1312, format="%.6f")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Efficiency Parameters Section
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("### Efficiency Model Parameters")
    
    hydrogen_efficiency = st.slider(
        "Hydrogen Efficiency Rating", 
        min_value=40, 
        max_value=80, 
        value=60,
        help="Vehicle efficiency in miles per kilogram of hydrogen"
    )
    
    elevation_penalty = st.slider(
        "Elevation Impact Factor", 
        min_value=10, 
        max_value=50, 
        value=25,
        help="Meters of elevation gain equivalent to one additional mile of travel"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Analysis Control
    st.markdown("---")
    analyze_button = st.button(
        "Execute Route Analysis",
        type="primary",
        use_container_width=True
    )

# Your existing analysis functions (keep these the same)
def analyze_routes(api_key, start, end, via_points, hydrogen_eff=60, elev_penalty=25):
    """Main function to analyze route efficiency"""
    if not api_key:
        st.error("API configuration required for route analysis")
        return None
    
    try:
        client = openrouteservice.Client(key=api_key)
        
        routes_coords = {
            "Route 1 (Direct)": [start, end],
            "Route 2 (Via Fremont)": [start, via_points[0], end],
            "Route 3 (Via Dumbarton)": [start, via_points[1], end]
        }
        
        all_routes = []
        
        with st.spinner("Processing route data..."):
            for route_name, coords in routes_coords.items():
                route = client.directions(
                    coordinates=coords,
                    profile='driving-car',
                    format='geojson',
                    validate=True,
                    instructions=False
                )
                geom = LineString(route['features'][0]['geometry']['coordinates'])
                all_routes.append({'route_id': route_name, 'geometry': geom})
        
        gdf = gpd.GeoDataFrame(all_routes, crs='EPSG:4326')
        
        # Sample points along routes for elevation analysis
        def sample_points(line, spacing_meters=500):
            line_proj = line.to_crs(epsg=3310)
            length = line_proj.geometry.length.values[0]
            distances = np.arange(0, length, spacing_meters)
            sampled_points = [line_proj.geometry.values[0].interpolate(d) for d in distances]
            return gpd.GeoDataFrame(geometry=sampled_points, crs='EPSG:3310').to_crs(epsg=4326)
        
        all_points = []
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
                st.warning(f"Elevation API issue: {str(e)}")
                return [np.nan] * len(latlons)
        
        with st.spinner("Fetching elevation data..."):
            latlons = [(pt.y, pt.x) for pt in points_gdf.geometry]
            batch_size = 100
            batches = [latlons[i:i+batch_size] for i in range(0, len(latlons), batch_size)]
            
            elevations = []
            for i, batch in enumerate(batches):
                elevations += get_elevation_batch(batch)
                time.sleep(0.5)
            
            points_gdf['elevation_m'] = elevations
        
        # Calculate elevation gain
        elevation_gain = []
        for route in points_gdf['route_id'].unique():
            route_points = points_gdf[points_gdf['route_id'] == route].sort_index()
            diff = route_points['elevation_m'].diff()
            gain = diff[diff > 0].sum()
            elevation_gain.append({'route_id': route, 'elevation_gain_m': gain})
        
        gain_df = pd.DataFrame(elevation_gain)
        
        # Calculate distances and efficiency
        gdf['distance_miles'] = gdf.to_crs(epsg=3310).geometry.length / 1609.34
        df = gdf[['route_id', 'distance_miles']].merge(gain_df, on='route_id')
        
        # Compute adjusted effective distance
        df['effective_miles'] = df['distance_miles'] + (df['elevation_gain_m'] / elev_penalty)
        
        # Hydrogen consumption
        df['hydrogen_kg'] = df['effective_miles'] / hydrogen_eff
        df['hydrogen_per_mile'] = df['hydrogen_kg'] / df['distance_miles']
        
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
        st.error(f"Route analysis error: {str(e)}")
        return None

# Main content area
if analyze_button:
    start_coord = [start_lon, start_lat]
    end_coord = [end_lon, end_lat]
    via_points = [[via1_lon, via1_lat], [via2_lon, via2_lat]]
    
    result = analyze_routes(api_key, start_coord, end_coord, via_points, hydrogen_efficiency, elevation_penalty)
    
    if result:
        df, gdf, segment_gdf, points_gdf = result
        
        # Professional Results Header
        st.markdown("## Route Analysis Results")
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        
        # Key Metrics in Professional Cards
        best_route = df.loc[df['hydrogen_kg'].idxmin()]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Optimal Route</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{best_route["route_id"]}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Fuel Consumption</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{best_route["hydrogen_kg"]:.2f} kg</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            shortest_route = df.loc[df['distance_miles'].idxmin()]
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Minimum Distance</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{shortest_route["distance_miles"]:.1f} mi</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            min_elev_route = df.loc[df['elevation_gain_m'].idxmin()]
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Elevation Gain</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{min_elev_route["elevation_gain_m"]:.0f} m</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Detailed Analysis Section
        st.markdown('<div class="section-header">Detailed Route Comparison</div>', unsafe_allow_html=True)
        
        # Professional Data Table
        display_df = df.copy()
        display_df['distance_miles'] = display_df['distance_miles'].round(1)
        display_df['elevation_gain_m'] = display_df['elevation_gain_m'].round(0)
        display_df['effective_miles'] = display_df['effective_miles'].round(1)
        display_df['hydrogen_kg'] = display_df['hydrogen_kg'].round(3)
        display_df['hydrogen_per_mile'] = (display_df['hydrogen_per_mile'] * 1000).round(1)
        
        display_df = display_df.rename(columns={
            'route_id': 'Route',
            'distance_miles': 'Distance (miles)',
            'elevation_gain_m': 'Elevation Gain (m)',
            'effective_miles': 'Effective Distance (miles)',
            'hydrogen_kg': 'Hydrogen (kg)',
            'hydrogen_per_mile': 'Efficiency (g/mile)'
        })
        
        # Style the table
        def highlight_optimal(row):
            if row['Hydrogen (kg)'] == df['hydrogen_kg'].min():
                return ['background-color: #d4edda', 'font-weight: bold'] * len(row)
            else:
                return [''] * len(row)
        
        st.dataframe(
            display_df.style.apply(highlight_optimal, axis=1),
            use_container_width=True
        )
        
        # Visualization Section
        st.markdown('<div class="section-header">Route Visualization</div>', unsafe_allow_html=True)
        
        col5, col6 = st.columns([2, 1])
        
        with col5:
            st.markdown("**Route Map with Elevation Analysis**")
            # Your existing map code here
            center = [points_gdf.geometry.y.mean(), points_gdf.geometry.x.mean()]
            m = folium.Map(location=center, zoom_start=10, tiles='CartoDB positron')
            
            colormap = cm.linear.RdYlGn_11.scale(
                segment_gdf['grade_pct'].min(), 
                segment_gdf['grade_pct'].max()
            )
            colormap = colormap.to_step(n=10)
            
            route_colors = {'Route 1 (Direct)': 'blue', 
                          'Route 2 (Via Fremont)': 'red', 
                          'Route 3 (Via Dumbarton)': 'green'}
            
            for _, row in segment_gdf.iterrows():
                color = colormap(row['grade_pct']) if not np.isnan(row['grade_pct']) else "#999999"
                folium.PolyLine(
                    locations=[(pt[1], pt[0]) for pt in row['geometry'].coords],
                    color=route_colors.get(row['route_id'], color),
                    weight=4,
                    tooltip=f"Route: {row['route_id']}<br>Grade: {row['grade_pct']:.2f}%",
                    opacity=0.8
                ).add_to(m)
            
            folium.Marker([start_lat, start_lon], popup="Origin", tooltip="Origin").add_to(m)
            folium.Marker([end_lat, end_lon], popup="Destination", tooltip="Destination").add_to(m)
            
            colormap.caption = "Route Segment Grade (%)"
            colormap.add_to(m)
            
            folium_static(m, width=700, height=500)
        
        with col6:
            st.markdown("**Efficiency Analysis**")
            
            # Professional chart styling
            fig, ax = plt.subplots(figsize=(8, 6))
            routes = df['route_id']
            hydrogen_kg = df['hydrogen_kg']
            
            colors = ['#3498db' if x != min(hydrogen_kg) else '#27ae60' for x in hydrogen_kg]
            
            bars = ax.bar(routes, hydrogen_kg, color=colors, alpha=0.8)
            ax.set_ylabel('Hydrogen Consumption (kg)', fontsize=12)
            ax.set_title('Route Efficiency Comparison', fontsize=14, fontweight='bold')
            plt.xticks(rotation=45, ha='right')
            ax.grid(True, alpha=0.3)
            
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                       f'{height:.3f}', ha='center', va='bottom', fontweight='bold')
            
            st.pyplot(fig)
        
        # Export Section
        st.markdown('<div class="section-header">Data Export</div>', unsafe_allow_html=True)
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download Analysis Results",
            data=csv,
            file_name="hydrogen_route_analysis.csv",
            mime="text/csv",
            use_container_width=True
        )

else:
    # Professional Welcome/Instructions
    st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
    st.markdown("### Welcome to the Hydrogen Route Efficiency Analyzer")
    st.markdown("""
    This advanced analysis tool evaluates multiple routes between specified locations, 
    calculating hydrogen fuel consumption while accounting for distance and elevation factors.
    """)
    
    st.markdown("#### Getting Started:")
    st.markdown("""
    1. Configure your API key in the sidebar (required for routing data)
    2. Set origin and destination coordinates  
    3. Adjust efficiency parameters based on your vehicle specifications
    4. Execute the analysis to compare route options
    """)
    
    st.markdown("""
    **Note:** The analysis incorporates real elevation data and calculates 
    adjusted energy requirements based on terrain characteristics.
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Feature highlights in cards
    st.markdown('<div class="section-header">Analysis Features</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Route Optimization</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size: 0.9rem; color: #2c3e50;">Multiple route comparison with elevation-aware efficiency scoring</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Fuel Modeling</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size: 0.9rem; color: #2c3e50;">Hydrogen consumption calculations with terrain impact analysis</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Data Visualization</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size: 0.9rem; color: #2c3e50;">Interactive maps and comparative charts for route analysis</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# Professional Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #7f8c8d; font-size: 0.9rem;'>
    Hydrogen Route Efficiency Analyzer • Advanced Fuel Consumption Modeling • Data Sources: OpenRouteService, Open-Elevation
</div>
""", unsafe_allow_html=True)
