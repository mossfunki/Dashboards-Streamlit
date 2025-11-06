import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta
import time

# Page configuration
st.set_page_config(
    page_title="Skills Gap Heat Map",
    page_icon="🔥",
    layout="wide"
)

class SkillsGapAnalyzer:
    def __init__(self):
        self.states = {
            'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
            'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
            'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
            'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
            'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
            'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
            'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
            'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
            'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
            'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming'
        }
    
    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def get_job_postings_data(_self, profession):
        """Simulate job postings data from APIs"""
        # In production, replace with real API calls to:
        # - Indeed API, LinkedIn Jobs API, USAJOBS API
        
        np.random.seed(hash(profession) % 10000)  # Consistent randomness per profession
        
        job_data = []
        for state, state_name in _self.states.items():
            # Base demand varies by state and profession
            base_demand = {
                'Data Scientist': np.random.randint(50, 500),
                'Software Engineer': np.random.randint(100, 800),
                'Cybersecurity Analyst': np.random.randint(30, 300),
                'Healthcare IT Manager': np.random.randint(20, 200),
                'AI Engineer': np.random.randint(10, 150),
                'Cloud Architect': np.random.randint(25, 250),
                'DevOps Engineer': np.random.randint(40, 350)
            }.get(profession, np.random.randint(50, 300))
            
            # Add some realistic geographic patterns
            tech_hubs = ['CA', 'WA', 'TX', 'NY', 'MA', 'CO', 'NC']
            if state in tech_hubs:
                base_demand = int(base_demand * 1.5)
            
            job_data.append({
                'state': state,
                'state_name': state_name,
                'job_openings': max(10, int(np.random.normal(base_demand, base_demand * 0.3))),
                'avg_salary': np.random.randint(80000, 160000),
                'growth_rate': np.random.uniform(0.05, 0.25)
            })
        
        return pd.DataFrame(job_data)
    
    @st.cache_data(ttl=86400)  # Cache for 24 hours
    def get_professional_supply_data(_self, profession):
        """Simulate professional supply data"""
        # In production, replace with:
        # - LinkedIn Profile API, BLS Data, Census Data
        
        np.random.seed(hash(profession) % 10000)
        
        supply_data = []
        for state, state_name in _self.states.items():
            # Base supply with realistic patterns
            base_supply = {
                'Data Scientist': np.random.randint(100, 1000),
                'Software Engineer': np.random.randint(200, 2000),
                'Cybersecurity Analyst': np.random.randint(50, 600),
                'Healthcare IT Manager': np.random.randint(30, 400),
                'AI Engineer': np.random.randint(20, 300),
                'Cloud Architect': np.random.randint(40, 500),
                'DevOps Engineer': np.random.randint(60, 700)
            }.get(profession, np.random.randint(100, 800))
            
            # Established tech hubs have more professionals
            established_hubs = ['CA', 'NY', 'TX', 'MA', 'WA', 'IL', 'VA']
            if state in established_hubs:
                base_supply = int(base_supply * 1.8)
            
            supply_data.append({
                'state': state,
                'state_name': state_name,
                'professionals': max(20, int(np.random.normal(base_supply, base_supply * 0.4))),
                'salary_expectation': np.random.randint(70000, 150000),
                'experience_years': np.random.uniform(3, 12)
            })
        
        return pd.DataFrame(supply_data)
    
    def calculate_skills_gap(self, job_data, supply_data):
        """Calculate supply-demand mismatch metrics"""
        merged_data = pd.merge(job_data, supply_data, on=['state', 'state_name'])
        
        merged_data['supply_demand_ratio'] = merged_data['job_openings'] / merged_data['professionals']
        merged_data['salary_premium'] = (merged_data['avg_salary'] - merged_data['salary_expectation']) / merged_data['salary_expectation']
        
        # Calculate opportunity score (0-100)
        merged_data['opportunity_score'] = (
            (merged_data['supply_demand_ratio'] / merged_data['supply_demand_ratio'].max() * 50) +
            (merged_data['salary_premium'] / merged_data['salary_premium'].max() * 30) +
            (merged_data['growth_rate'] / merged_data['growth_rate'].max() * 20)
        )
        
        # Categorize opportunity level
        def get_opportunity_level(score):
            if score >= 70: return 'CRITICAL GAP'
            elif score >= 50: return 'HIGH OPPORTUNITY'
            elif score >= 30: return 'MODERATE OPPORTUNITY'
            else: return 'BALANCED'
        
        merged_data['opportunity_level'] = merged_data['opportunity_score'].apply(get_opportunity_level)
        
        return merged_data
    
    def create_heat_map(self, gap_data, profession):
        """Create interactive heat map"""
        fig = px.choropleth(
            gap_data,
            locations='state',
            locationmode='USA-states',
            color='opportunity_score',
            scope='usa',
            color_continuous_scale='RdYlGn_r',  # Red (high gap) to Green (balanced)
            range_color=(0, 100),
            title=f'{profession} - Skills Gap Heat Map<br><sub>Red: High Demand Gap | Green: Balanced Market</sub>',
            hover_data={
                'state_name': True,
                'job_openings': True,
                'professionals': True,
                'supply_demand_ratio': ':.2f',
                'avg_salary': '$,.0f',
                'opportunity_level': True
            },
            labels={
                'opportunity_score': 'Opportunity Score',
                'state_name': 'State',
                'job_openings': 'Job Openings',
                'professionals': 'Local Professionals',
                'supply_demand_ratio': 'Jobs per Professional',
                'avg_salary': 'Avg Salary'
            }
        )
        
        fig.update_layout(
            height=600,
            geo=dict(bgcolor='rgba(0,0,0,0)'),
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(size=12)
        )
        
        return fig

# Initialize analyzer
analyzer = SkillsGapAnalyzer()

# Main dashboard
st.title("🔥 Skills Gap Heat Map")
st.markdown("### Discover where your skills are in highest demand")

# Profession selection
professions = [
    'Data Scientist', 'Software Engineer', 'Cybersecurity Analyst',
    'Healthcare IT Manager', 'AI Engineer', 'Cloud Architect', 'DevOps Engineer'
]

col1, col2 = st.columns([1, 2])

with col1:
    selected_profession = st.selectbox(
        "Select Your Profession",
        professions,
        index=0
    )
    
    st.markdown("---")
    st.markdown("**How to read the map:**")
    st.markdown("🔴 **Red**: Critical shortage (high opportunity)")
    st.markdown("🟡 **Yellow**: Moderate gap")
    st.markdown("🟢 **Green**: Balanced market")
    
    # Auto-refresh toggle
    auto_refresh = st.checkbox("Auto-refresh data (every 30 min)", value=False)
    if auto_refresh:
        time.sleep(1800)  # 30 minutes
        st.rerun()

with col2:
    st.info(f"💡 **Analyzing**: {selected_profession} market across all US states")

# Load and analyze data
with st.spinner("Loading real-time market data..."):
    job_data = analyzer.get_job_postings_data(selected_profession)
    supply_data = analyzer.get_professional_supply_data(selected_profession)
    gap_data = analyzer.calculate_skills_gap(job_data, supply_data)

# Display heat map
st.plotly_chart(analyzer.create_heat_map(gap_data, selected_profession), use_container_width=True)

# Top opportunities table
st.subheader("🎯 Top 10 Highest Opportunity Markets")

top_opportunities = gap_data.nlargest(10, 'opportunity_score')[[
    'state_name', 'job_openings', 'professionals', 'supply_demand_ratio',
    'avg_salary', 'opportunity_level'
]]

# Format the table
top_opportunities_display = top_opportunities.copy()
top_opportunities_display['supply_demand_ratio'] = top_opportunities_display['supply_demand_ratio'].round(2)
top_opportunities_display['avg_salary'] = top_opportunities_display['avg_salary'].apply(lambda x: f"${x:,.0f}")

st.dataframe(
    top_opportunities_display.rename(columns={
        'state_name': 'State',
        'job_openings': 'Job Openings',
        'professionals': 'Local Professionals',
        'supply_demand_ratio': 'Jobs per Professional',
        'avg_salary': 'Average Salary',
        'opportunity_level': 'Opportunity Level'
    }),
    use_container_width=True
)

# Detailed analysis
st.subheader("📊 Market Analysis")

col1, col2, col3 = st.columns(3)

with col1:
    total_jobs = gap_data['job_openings'].sum()
    st.metric("Total US Job Openings", f"{total_jobs:,}")

with col2:
    avg_ratio = gap_data['supply_demand_ratio'].mean()
    st.metric("Avg Jobs per Professional", f"{avg_ratio:.2f}")

with col3:
    critical_gaps = len(gap_data[gap_data['opportunity_level'] == 'CRITICAL GAP'])
    st.metric("Critical Gap States", f"{critical_gaps}")

# State comparison tool
st.subheader("🔍 Compare Specific States")

selected_states = st.multiselect(
    "Select states to compare:",
    options=gap_data['state_name'].tolist(),
    default=top_opportunities['state_name'].head(3).tolist()
)

if selected_states:
    comparison_data = gap_data[gap_data['state_name'].isin(selected_states)]
    
    fig_comparison = go.Figure()
    
    fig_comparison.add_trace(go.Bar(
        name='Job Openings',
        x=comparison_data['state_name'],
        y=comparison_data['job_openings'],
        marker_color='lightblue'
    ))
    
    fig_comparison.add_trace(go.Bar(
        name='Local Professionals',
        x=comparison_data['state_name'],
        y=comparison_data['professionals'],
        marker_color='lightcoral'
    ))
    
    fig_comparison.update_layout(
        title='Supply vs Demand Comparison',
        barmode='group',
        height=400
    )
    
    st.plotly_chart(fig_comparison, use_container_width=True)

# Relocation calculator
st.subheader("💼 Relocation Opportunity Calculator")

col1, col2, col3 = st.columns(3)

with col1:
    current_state = st.selectbox("Your Current State", gap_data['state_name'].tolist())

with col2:
    target_state = st.selectbox("Target State", gap_data['state_name'].tolist())

with col3:
    current_salary = st.number_input("Your Current Salary", value=100000, step=10000)

if current_state and target_state and current_salary:
    current_data = gap_data[gap_data['state_name'] == current_state].iloc[0]
    target_data = gap_data[gap_data['state_name'] == target_state].iloc[0]
    
    # Calculate opportunity
    salary_change = target_data['avg_salary'] - current_salary
    salary_change_pct = (salary_change / current_salary) * 100
    competition_change = target_data['supply_demand_ratio'] - current_data['supply_demand_ratio']
    
    st.markdown("### 📈 Relocation Analysis")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Salary Change", f"${salary_change:+,.0f}", f"{salary_change_pct:+.1f}%")
    
    with col2:
        st.metric("Job Competition", f"{competition_change:+.2f}", "jobs per pro")
    
    with col3:
        opportunity_improvement = target_data['opportunity_score'] - current_data['opportunity_score']
        st.metric("Opportunity Score", f"{opportunity_improvement:+.0f} pts")

# Data last updated
st.markdown("---")
st.caption(f"📅 Data last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.caption("💡 This dashboard uses simulated data. Real API integration would provide live market data.")

# API Integration Notes
with st.expander("🔧 Planned API Integrations"):
    st.markdown("""
    **Real Data Sources to Integrate:**
    
    - **Job Demand Data:**
      - Indeed API (job postings by location)
      - LinkedIn Jobs API
      - USAJOBS API (government positions)
      - Google Jobs API
    
    - **Professional Supply Data:**
      - LinkedIn Profile API (professional density)
      - Bureau of Labor Statistics API
      - Census Bureau API
    
    - **Salary & Cost Data:**
      - Glassdoor Salary API
      - Zillow API (cost of living)
      - Bureau of Economic Analysis API
    """)
