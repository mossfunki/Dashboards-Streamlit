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
    page_icon="🚗",
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

# Professional Sidebar Layout
with st.sidebar:
    # Sidebar Header
    st.markdown("""
    <div style='text-align: center; margin-bottom: 2rem;'>
        <h2 style='color: #2c3e50; margin-bottom: 0.5rem;'>Route Configuration</h2>
        <div style='color: #7f8c8d; font-size: 0.9rem;'>Enter your start and end locations</div>
    </div>
    """, unsafe_allow_html=True)
    
    # API Configuration Section
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("### API Settings")
    
    if api_key:
        st.markdown('<div class="success-status">✓ API Key: Configured</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="warning-status">⚠ API Key Required</div>', unsafe_allow_html=True)
        api_key = st.text_input("OpenRouteService API Key", type="password", label_visibility="collapsed",
                               help="Get a free API key from https://openrouteservice.org/")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Simple Location Input Section
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("### Journey Details")
    
    # Simple address input or coordinate input
    input_method = st.radio("Input method:", ["Coordinates", "City Names"], horizontal=True)
    
    if input_method == "Coordinates":
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Start Location**")
            start_lat = st.number_input("Latitude", value=37.8044, format="%.6f", key="start_lat")
            start_lon = st.number_input("Longitude", value=-122.2711, format="%.6f", key="start_lon")
        
        with col2:
            st.markdown("**End Location**")
            end_lat = st.number_input("Latitude", value=37.3382, format="%.6f", key="end_lat")
            end_lon = st.number_input("Longitude", value=-121.8863, format="%.6f", key="end_lon")
    
    else:  # City Names
        col1, col2 = st.columns(2)
        with col1:
            start_city = st.text_input("From City", value="Oakland, CA")
        with col2:
            end_city = st.text_input("To City", value="San Jose, CA")
        
        # For demo purposes - in a real app you'd geocode these
        start_lat, start_lon = 37.8044, -122.2711  # Oakland
        end_lat, end_lon = 37.3382, -121.8863  # San Jose
        
        st.info("📍 Using demo coordinates for Oakland to San Jose")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Vehicle Efficiency Section
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("### Vehicle Efficiency Settings")
    
    # Improved Hydrogen Efficiency Slider
    st.markdown("**Vehicle Fuel Efficiency**")
    hydrogen_efficiency = st.slider(
        "Miles per kilogram of hydrogen", 
        min_value=40, 
        max_value=100, 
        value=65,
        help="How many miles your vehicle can travel on 1 kg of hydrogen fuel"
    )
    
    # Show real-world context
    efficiency_context = ""
    if hydrogen_efficiency <= 50:
        efficiency_context = " (Similar to early fuel cell vehicles)"
    elif hydrogen_efficiency <= 70:
        efficiency_context = " (Typical modern fuel cell vehicle)"
    else:
        efficiency_context = " (High-efficiency advanced models)"
    
    st.markdown(f'<div class="slider-help">Current setting: {hydrogen_efficiency} miles/kg{efficiency_context}</div>', unsafe_allow_html=True)
    
    # Improved Elevation Impact Slider
    st.markdown("**Elevation Sensitivity**")
    elevation_penalty = st.slider(
        "Energy cost of elevation gain", 
        min_value=10, 
        max_value=50, 
        value=25,
        help="How much extra energy is required for climbing hills"
    )
    
    # Show mathematical interpretation
    penalty_interpretation = f"1 meter climb = {1/elevation_penalty:.3f} extra miles of flat travel"
    st.markdown(f'<div class="slider-help">{penalty_interpretation}</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Analysis Control
    st.markdown("---")
    analyze_button = st.button(
        "Find Most Efficient Route",
        type="primary",
        use_container_width=True,
        help="Analyze all possible routes and find the one with lowest hydrogen consumption"
    )

# Enhanced analysis function that explores multiple routes
def analyze_routes_enhanced(api_key, start, end, hydrogen_eff=65, elev_penalty=25):
    """Enhanced function to analyze multiple route options automatically"""
    if not api_key:
        st.error("API configuration required for route analysis")
        return None
    
    try:
        client = openrouteservice.Client(key=api_key)
        
        # Generate multiple route options by varying parameters
        route_options = []
        
        # Direct route (fastest)
        with st.spinner("Finding fastest route..."):
            try:
                direct_route = client.directions(
                    coordinates=[start, end],
                    profile='driving-car',
                    format='geojson',
                    validate=True,
                    instructions=False,
                    options={"avoid_features": ["ferries", "tollways"]}
                )
                route_options.append(("Fastest Route", direct_route))
            except Exception as e:
                st.warning(f"Could not get fastest route: {e}")
        
        # Alternative route 1 (shorter distance)
        with st.spinner("Finding shorter route..."):
            try:
                short_route = client.directions(
                    coordinates=[start, end],
                    profile='driving-car',
                    format='geojson',
                    validate=True,
                    instructions=False,
                    options={"avoid_features": ["highways", "ferries", "tollways"]}
                )
                route_options.append(("Shorter Route", short_route))
            except Exception as e:
                st.warning(f"Could not get shorter route: {e}")
        
        # Alternative route 2 (scenic/avoid highways)
        with st.spinner("Finding alternative route..."):
            try:
                scenic_route = client.directions(
                    coordinates=[start, end],
                    profile='driving-car',
                    format='geojson',
                    validate=True,
                    instructions=False,
                    options={"avoid_features": ["highways"]}
                )
                route_options.append(("Highway Avoidance Route", scenic_route))
            except Exception as e:
                st.warning(f"Could not get alternative route: {e}")
        
        if not route_options:
            st.error("No routes could be found. Please check your coordinates and API key.")
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
        df['hydrogen_per_km'] = (df['hydrogen_kg'] / df['distance_km'] * 1000)  # grams per km
        df['hydrogen_per_mile'] = (df['hydrogen_kg'] / df['distance_miles'] * 1000)  # grams per mile
        
        # Calculate cost savings compared to worst route
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
        st.error(f"Route analysis error: {str(e)}")
        return None

# Main content area
if analyze_button and api_key:
    start_coord = [start_lon, start_lat]
    end_coord = [end_lon, end_lat]
    
    result = analyze_routes_enhanced(api_key, start_coord, end_coord, hydrogen_efficiency, elevation_penalty)
    
    if result:
        df, gdf, segment_gdf, points_gdf = result
        
        # Find the most efficient route
        best_route_row = df.loc[df['hydrogen_kg'].idxmin()]
        worst_route_row = df.loc[df['hydrogen_kg'].idxmax()]
        
        # Professional Results Header
        st.markdown("## Route Analysis Results")
        st.markdown("### 🎯 Recommended Route")
        
        # Highlight the best route
        st.markdown(f'<div class="success-status" style="font-size: 1.1rem;">'
                   f'<strong>Best Choice:</strong> {best_route_row["route_id"]} - '
                   f'Only {best_route_row["hydrogen_kg"]:.2f} kg hydrogen required'
                   f'</div>', unsafe_allow_html=True)
        
        # Key Comparison Metrics
        st.markdown("### Efficiency Comparison")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            savings_kg = worst_route_row['hydrogen_kg'] - best_route_row['hydrogen_kg']
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Fuel Savings</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{savings_kg:.2f} kg</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            savings_percent = (savings_kg / worst_route_row['hydrogen_kg'] * 100)
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Efficiency Gain</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{savings_percent:.1f}%</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Best Route Distance</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{best_route_row["distance_miles"]:.1f} mi</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Elevation Impact</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">+{best_route_row["effective_distance_miles"] - best_route_row["distance_miles"]:.1f} mi</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Detailed Route Comparison
        st.markdown("### Detailed Route Analysis")
        
        # Enhanced comparison table
        display_df = df.copy()
        display_df['Distance (mi)'] = display_df['distance_miles'].round(1)
        display_df['Elevation Gain (m)'] = display_df['elevation_gain_m'].round(0)
        display_df['Effective Dist (mi)'] = display_df['effective_distance_miles'].round(1)
        display_df['Hydrogen (kg)'] = display_df['hydrogen_kg'].round(3)
        display_df['Efficiency (g/mi)'] = display_df['hydrogen_per_mile'].round(1)
        display_df['Savings vs Worst'] = display_df['savings_percent'].apply(lambda x: f"{x}%")
        
        display_df = display_df[[
            'route_id', 'Distance (mi)', 'Elevation Gain (m)', 
            'Effective Dist (mi)', 'Hydrogen (kg)', 'Efficiency (g/mi)', 'Savings vs Worst'
        ]].rename(columns={'route_id': 'Route Option'})
        
        # Style the table with clear winner indication
        def highlight_recommended(row):
            if row['Hydrogen (kg)'] == best_route_row['hydrogen_kg']:
                return ['background-color: #d4edda', 'font-weight: bold'] * len(row)
            else:
                return [''] * len(row)
        
        st.dataframe(
            display_df.style.apply(highlight_recommended, axis=1),
            use_container_width=True
        )
        
        # Visualization Section
        st.markdown("### Route Visualization & Analysis")
        
        col5, col6 = st.columns([2, 1])
        
        with col5:
            st.markdown("**Interactive Route Map**")
            # Your existing map code here
            center = [points_gdf.geometry.y.mean(), points_gdf.geometry.x.mean()]
            m = folium.Map(location=center, zoom_start=10, tiles='CartoDB positron')
            
            # Color routes by efficiency
            route_colors = {}
            colors = ['#27ae60', '#3498db', '#e74c3c', '#f39c12', '#9b59b6']  # Green to red for best to worst
            
            sorted_routes = df.sort_values('hydrogen_kg')
            for i, (_, route_row) in enumerate(sorted_routes.iterrows()):
                route_colors[route_row['route_id']] = colors[i % len(colors)]
            
            for _, row in segment_gdf.iterrows():
                color = route_colors.get(row['route_id'], "#999999")
                folium.PolyLine(
                    locations=[(pt[1], pt[0]) for pt in row['geometry'].coords],
                    color=color,
                    weight=5,
                    tooltip=f"{row['route_id']}<br>Grade: {row['grade_pct']:.1f}%",
                    opacity=0.8
                ).add_to(m)
            
            folium.Marker([start_lat, start_lon], popup="Start", tooltip="Start", 
                         icon=folium.Icon(color='green')).add_to(m)
            folium.Marker([end_lat, end_lon], popup="End", tooltip="End",
                         icon=folium.Icon(color='red')).add_to(m)
            
            folium_static(m, width=700, height=500)
        
        with col6:
            st.markdown("**Fuel Consumption Comparison**")
            
            fig, ax = plt.subplots(figsize=(8, 6))
            routes = df['route_id']
            hydrogen_kg = df['hydrogen_kg']
            
            # Color bars from green (best) to red (worst)
            colors = ['#27ae60' if x == min(hydrogen_kg) else 
                     '#e74c3c' if x == max(hydrogen_kg) else 
                     '#3498db' for x in hydrogen_kg]
            
            bars = ax.bar(routes, hydrogen_kg, color=colors, alpha=0.8)
            ax.set_ylabel('Hydrogen Required (kg)', fontsize=12)
            ax.set_title('Route Efficiency Comparison', fontsize=14, fontweight='bold')
            plt.xticks(rotation=45, ha='right')
            ax.grid(True, alpha=0.3)
            
            # Add value labels
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                       f'{height:.3f} kg', ha='center', va='bottom', fontweight='bold',
                       fontsize=9)
            
            st.pyplot(fig)
            
            # Elevation impact explanation
            st.markdown("#### Why Routes Differ")
            best_elevation_impact = best_route_row['effective_distance_miles'] - best_route_row['distance_miles']
            st.markdown(f"""
            The recommended route saves fuel by minimizing elevation changes and optimizing distance.
            
            **Elevation impact on selected route:** +{best_elevation_impact:.1f} equivalent miles
            """)
        
        # Export Section
        st.markdown("### Export Results")
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download Complete Analysis",
            data=csv,
            file_name=f"hydrogen_route_analysis_{start_lat}_{start_lon}_to_{end_lat}_{end_lon}.csv",
            mime="text/csv",
            use_container_width=True
        )

elif analyze_button and not api_key:
    st.error("Please configure your OpenRouteService API key to analyze routes.")

else:
    # Enhanced Welcome Section
    st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
    st.markdown("### Welcome to the Hydrogen Route Efficiency Analyzer")
    st.markdown("""
    This intelligent system automatically finds and compares multiple route options between your 
    start and end locations, then identifies the most fuel-efficient path for your hydrogen vehicle.
    """)
    
    st.markdown("#### How It Works:")
    st.markdown("""
    1. **Enter your journey details** - Simply provide start and end locations
    2. **Configure your vehicle** - Set your vehicle's fuel efficiency and elevation sensitivity
    3. **Get smart recommendations** - The system analyzes multiple routes and recommends the most efficient one
    4. **Understand the trade-offs** - See how distance, elevation, and route choice affect fuel consumption
    """)
    
    st.markdown("""
    **Intelligent Analysis:** The system automatically explores fastest, shortest, and alternative routes, 
    then calculates precise hydrogen consumption considering both distance and elevation factors.
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Feature highlights
    st.markdown("### Key Features")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Automatic Route Discovery</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size: 0.9rem; color: #2c3e50;">Finds and compares multiple route options automatically</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Precision Fuel Modeling</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size: 0.9rem; color: #2c3e50;">Accurate hydrogen consumption calculations with elevation impact</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Smart Recommendations</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size: 0.9rem; color: #2c3e50;">Clear identification of the most efficient route with savings analysis</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# Professional Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #7f8c8d; font-size: 0.9rem;'>
    Hydrogen Route Efficiency Analyzer • Intelligent Route Optimization • Advanced Fuel Consumption Modeling
</div>
""", unsafe_allow_html=True)
