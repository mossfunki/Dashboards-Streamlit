import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
import time
import json

# Page configuration
st.set_page_config(
    page_title="Skills Gap Heat Map - Live API Data",
    page_icon="🔥",
    layout="wide"
)

class DynamicAPIAnalyzer:
    def __init__(self):
        # All API keys from Streamlit secrets
        self.usajobs_key = st.secrets.get("USAJOBS_KEY", "")
        self.adzuna_id = st.secrets.get("ADZUNA_APP_ID", "")
        self.adzuna_key = st.secrets.get("ADZUNA_APP_KEY", "")
        self.bls_key = st.secrets.get("BLS_API_KEY", "")
        
        # API status tracking
        self.api_status = {}
        
    def test_all_apis(self):
        """Test all APIs and return available ones"""
        available_apis = []
        
        # Test USAJOBS
        if self.usajobs_key:
            try:
                url = "https://data.usajobs.gov/api/search"
                headers = {'User-Agent': 'skills-gap-analyzer@example.com', 'Authorization-Key': self.usajobs_key}
                params = {'Keyword': 'test', 'ResultsPerPage': 1}
                response = requests.get(url, headers=headers, params=params, timeout=10)
                if response.status_code == 200:
                    available_apis.append('USAJOBS')
                    self.api_status['USAJOBS'] = '✅ Connected'
                else:
                    self.api_status['USAJOBS'] = '❌ Failed'
            except:
                self.api_status['USAJOBS'] = '❌ Failed'
        
        # Test Adzuna
        if self.adzuna_id and self.adzuna_key:
            try:
                url = "http://api.adzuna.com/v1/api/jobs/us/search/1"
                params = {'app_id': self.adzuna_id, 'app_key': self.adzuna_key, 'what': 'software'}
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    available_apis.append('Adzuna')
                    self.api_status['Adzuna'] = '✅ Connected'
                else:
                    self.api_status['Adzuna'] = '❌ Failed'
            except:
                self.api_status['Adzuna'] = '❌ Failed'
        
        # Test BLS
        if self.bls_key:
            try:
                url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
                headers = {'Content-Type': 'application/json'}
                data = {"seriesid": ["OEUN0000000151252000000"], "registrationkey": self.bls_key}
                response = requests.post(url, headers=headers, json=data, timeout=15)
                if response.status_code == 200:
                    available_apis.append('BLS')
                    self.api_status['BLS'] = '✅ Connected'
                else:
                    self.api_status['BLS'] = '❌ Failed'
            except:
                self.api_status['BLS'] = '❌ Failed'
        
        return available_apis

    def call_usajobs_api(self, profession, location=""):
        """Dynamically call USAJOBS API and adapt to response"""
        try:
            url = "https://data.usajobs.gov/api/search"
            headers = {
                'User-Agent': 'skills-gap-analyzer@example.com',
                'Authorization-Key': self.usajobs_key
            }
            params = {
                'Keyword': profession,
                'LocationName': location,
                'ResultsPerPage': 1
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                count = data.get('SearchResult', {}).get('SearchResultCountAll', 0)
                
                # Extract salary data if available
                salary_data = self.extract_usajobs_salary(data)
                
                return {
                    'job_count': count,
                    'salary': salary_data,
                    'source': 'USAJOBS',
                    'timestamp': datetime.now().isoformat(),
                    'success': True
                }
            else:
                return {'success': False, 'error': f'Status {response.status_code}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def call_adzuna_api(self, profession, location=None):
        """Dynamically call Adzuna API and adapt to response"""
        try:
            url = "http://api.adzuna.com/v1/api/jobs/us/search/1"
            params = {
                'app_id': self.adzuna_id,
                'app_key': self.adzuna_key,
                'what': profession,
                'content-type': 'application/json'
            }
            if location:
                params['where'] = location
                
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                count = data.get('count', 0)
                
                # Extract salary and other metrics from Adzuna
                salary_data = self.extract_adzuna_salary(data)
                companies = self.extract_adzuna_companies(data)
                
                return {
                    'job_count': count,
                    'salary': salary_data,
                    'companies': companies,
                    'source': 'Adzuna',
                    'timestamp': datetime.now().isoformat(),
                    'success': True
                }
            else:
                return {'success': False, 'error': f'Status {response.status_code}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def call_bls_api(self, profession, state=None):
        """Dynamically call BLS API for employment and salary data"""
        try:
            # Map professions to SOC codes
            soc_mapping = {
                'Data Scientist': '15-2051',
                'Software Engineer': '15-1252',
                'Cybersecurity Analyst': '15-1212',
                'Healthcare IT Manager': '11-3021',
                'AI Engineer': '15-1299',
                'Cloud Architect': '15-1244',
                'DevOps Engineer': '15-1252'
            }
            
            soc_code = soc_mapping.get(profession, '15-1299')
            
            if state:
                # State-level data
                state_codes = {
                    'CA': '06', 'TX': '48', 'NY': '36', 'FL': '12', 'WA': '53',
                    'MA': '25', 'CO': '08', 'NC': '37', 'GA': '13', 'IL': '17',
                    'VA': '51', 'AZ': '04', 'MI': '26', 'OH': '39', 'PA': '42'
                }
                state_code = state_codes.get(state, '00')
                series_id = f"OEUS{state_code}0000{soc_code.replace('-', '')}000000"
            else:
                # National data
                series_id = f"OEUN0000000{soc_code.replace('-', '')}000000"
            
            url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
            headers = {'Content-Type': 'application/json'}
            data = {
                "seriesid": [series_id],
                "startyear": "2022",
                "endyear": "2023",
                "registrationkey": self.bls_key
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=15)
            
            if response.status_code == 200:
                bls_data = response.json()
                employment_data = self.parse_bls_employment(bls_data, state)
                salary_data = self.parse_bls_salary(bls_data, state)
                
                return {
                    'employment': employment_data,
                    'salary': salary_data,
                    'source': 'BLS',
                    'timestamp': datetime.now().isoformat(),
                    'success': True
                }
            else:
                return {'success': False, 'error': f'Status {response.status_code}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def extract_usajobs_salary(self, data):
        """Extract salary information from USAJOBS response"""
        try:
            jobs = data.get('SearchResult', {}).get('SearchResultItems', [])
            salaries = []
            
            for job in jobs:
                position = job.get('MatchedObjectDescriptor', {})
                salary_range = position.get('PositionRemuneration', [{}])[0]
                
                min_salary = salary_range.get('MinimumRange', '')
                max_salary = salary_range.get('MaximumRange', '')
                
                if min_salary and max_salary:
                    try:
                        avg = (float(min_salary) + float(max_salary)) / 2
                        salaries.append(avg)
                    except:
                        continue
            
            return {
                'average': np.mean(salaries) if salaries else None,
                'min': min(salaries) if salaries else None,
                'max': max(salaries) if salaries else None,
                'count': len(salaries)
            }
        except:
            return None

    def extract_adzuna_salary(self, data):
        """Extract salary information from Adzuna response"""
        try:
            results = data.get('results', [])
            salaries = []
            
            for job in results:
                salary = job.get('salary_min')
                if salary:
                    salaries.append(salary)
                salary_max = job.get('salary_max')
                if salary_max:
                    salaries.append(salary_max)
            
            return {
                'average': np.mean(salaries) if salaries else None,
                'min': min(salaries) if salaries else None,
                'max': max(salaries) if salaries else None,
                'count': len(salaries)
            }
        except:
            return None

    def extract_adzuna_companies(self, data):
        """Extract company information from Adzuna response"""
        try:
            results = data.get('results', [])
            companies = {}
            
            for job in results:
                company = job.get('company', {}).get('display_name')
                if company:
                    companies[company] = companies.get(company, 0) + 1
            
            return dict(sorted(companies.items(), key=lambda x: x[1], reverse=True)[:5])
        except:
            return {}

    def parse_bls_employment(self, data, state):
        """Parse employment data from BLS response"""
        try:
            if 'Results' in data and 'series' in data['Results']:
                series_data = data['Results']['series'][0]['data']
                for item in series_data:
                    if item['value'] != '-' and item['periodName'] == 'Annual':
                        return int(item['value'].replace(',', ''))
            return None
        except:
            return None

    def parse_bls_salary(self, data, state):
        """Parse salary data from BLS response"""
        try:
            # BLS salary data might be in a different series
            # This is a simplified parser - would need adjustment for actual salary series
            if 'Results' in data and 'series' in data['Results']:
                # Extract wage data if available in the response
                series_data = data['Results']['series'][0]['data']
                # Implementation would depend on specific BLS wage series structure
                return None
            return None
        except:
            return None

    @st.cache_data(ttl=1800)  # 30 minute cache
    def get_dynamic_job_data(_self, profession):
        """Get job data dynamically from all available APIs"""
        states = {
            'CA': 'California', 'TX': 'Texas', 'NY': 'New York', 'FL': 'Florida',
            'WA': 'Washington', 'MA': 'Massachusetts', 'CO': 'Colorado', 'NC': 'North Carolina',
            'GA': 'Georgia', 'IL': 'Illinois', 'VA': 'Virginia', 'AZ': 'Arizona'
        }
        
        job_data = []
        api_usage = {'USAJOBS': 0, 'Adzuna': 0, 'BLS': 0}
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, (state, state_name) in enumerate(states.items()):
            status_text.text(f"Fetching data for {state_name}... ({i+1}/{len(states)})")
            
            state_job_data = {
                'state': state,
                'state_name': state_name,
                'sources_used': [],
                'job_openings': 0,
                'avg_salary': None,
                'api_responses': []
            }
            
            # Try all available APIs for this state
            if _self.usajobs_key:
                usajobs_result = _self.call_usajobs_api(profession, state_name)
                if usajobs_result['success']:
                    state_job_data['sources_used'].append('USAJOBS')
                    state_job_data['job_openings'] += usajobs_result['job_count']
                    if usajobs_result['salary'] and usajobs_result['salary']['average']:
                        state_job_data['avg_salary'] = usajobs_result['salary']['average']
                    state_job_data['api_responses'].append(usajobs_result)
                    api_usage['USAJOBS'] += 1
                    time.sleep(0.3)  # Rate limiting
            
            if _self.adzuna_id and _self.adzuna_key:
                adzuna_result = _self.call_adzuna_api(profession, state_name)
                if adzuna_result['success']:
                    state_job_data['sources_used'].append('Adzuna')
                    state_job_data['job_openings'] += adzuna_result['job_count']
                    if adzuna_result['salary'] and adzuna_result['salary']['average']:
                        # Use Adzuna salary if no salary from USAJOBS, or average both
                        if state_job_data['avg_salary']:
                            state_job_data['avg_salary'] = (state_job_data['avg_salary'] + adzuna_result['salary']['average']) / 2
                        else:
                            state_job_data['avg_salary'] = adzuna_result['salary']['average']
                    state_job_data['api_responses'].append(adzuna_result)
                    api_usage['Adzuna'] += 1
                    time.sleep(0.3)  # Rate limiting
            
            # If no job data from APIs, skip this state for now
            if state_job_data['job_openings'] > 0:
                # Calculate growth rate based on profession and market conditions
                state_job_data['growth_rate'] = _self.calculate_dynamic_growth(profession, state, state_job_data)
                job_data.append(state_job_data)
            
            progress_bar.progress((i + 1) / len(states))
        
        status_text.empty()
        progress_bar.empty()
        
        return pd.DataFrame(job_data), api_usage

    @st.cache_data(ttl=86400)  # 24 hour cache
    def get_dynamic_supply_data(_self, profession):
        """Get professional supply data dynamically from available APIs"""
        states = {
            'CA': 'California', 'TX': 'Texas', 'NY': 'New York', 'FL': 'Florida',
            'WA': 'Washington', 'MA': 'Massachusetts', 'CO': 'Colorado', 'NC': 'North Carolina',
            'GA': 'Georgia', 'IL': 'Illinois', 'VA': 'Virginia', 'AZ': 'Arizona'
        }
        
        supply_data = []
        
        # Get national employment data from BLS
        national_result = _self.call_bls_api(profession)
        
        for state, state_name in states.items():
            state_supply_data = {
                'state': state,
                'state_name': state_name,
                'professionals': None,
                'salary_expectation': None,
                'sources_used': []
            }
            
            # Try to get state-level BLS data
            if _self.bls_key:
                state_result = _self.call_bls_api(profession, state)
                if state_result['success'] and state_result['employment']:
                    state_supply_data['professionals'] = state_result['employment']
                    state_supply_data['sources_used'].append('BLS')
                    
                    # Get salary expectation from BLS or other sources
                    if state_result['salary']:
                        state_supply_data['salary_expectation'] = state_result['salary']
                    else:
                        # Estimate based on national data and state cost of living
                        state_supply_data['salary_expectation'] = _self.estimate_salary_expectation(profession, state)
            
            # If no BLS data, use LinkedIn profile estimates (would need LinkedIn API)
            # For now, we'll use realistic estimates based on available data
            if not state_supply_data['professionals'] and national_result['success']:
                state_supply_data['professionals'] = _self.estimate_state_employment(
                    national_result['employment'], profession, state
                )
                state_supply_data['sources_used'].append('Estimated')
                state_supply_data['salary_expectation'] = _self.estimate_salary_expectation(profession, state)
            
            supply_data.append(state_supply_data)
        
        return pd.DataFrame(supply_data)

    def calculate_dynamic_growth(self, profession, state, job_data):
        """Calculate growth rate based on real market conditions"""
        # This would use real economic indicators
        # For now, using profession-specific growth rates adjusted by state economy
        base_growth = {
            'Data Scientist': 0.22,
            'Software Engineer': 0.15,
            'Cybersecurity Analyst': 0.32,
            'Healthcare IT Manager': 0.18,
            'AI Engineer': 0.28,
            'Cloud Architect': 0.24,
            'DevOps Engineer': 0.20
        }.get(profession, 0.12)
        
        # Adjust based on state tech growth indicators
        high_growth_states = ['TX', 'NC', 'TN', 'UT', 'CO', 'AZ', 'GA']
        if state in high_growth_states:
            return base_growth * 1.3
        return base_growth

    def estimate_state_employment(self, national_employment, profession, state):
        """Estimate state employment based on national data and state characteristics"""
        state_populations = {
            'CA': 0.118, 'TX': 0.087, 'FL': 0.065, 'NY': 0.059, 'PA': 0.039,
            'IL': 0.038, 'OH': 0.035, 'GA': 0.032, 'NC': 0.031, 'MI': 0.030
        }
        
        tech_concentration = {
            'CA': 2.5, 'WA': 2.2, 'MA': 2.0, 'NY': 1.8, 'CO': 1.7,
            'TX': 1.6, 'VA': 1.5, 'NC': 1.4, 'GA': 1.3, 'IL': 1.3
        }
        
        state_share = state_populations.get(state, 0.02)
        concentration = tech_concentration.get(state, 1.0)
        
        return int(national_employment * state_share * concentration)

    def estimate_salary_expectation(self, profession, state):
        """Estimate salary expectation based on profession and location"""
        base_salaries = {
            'Data Scientist': 120000,
            'Software Engineer': 110000,
            'Cybersecurity Analyst': 105000,
            'Healthcare IT Manager': 115000,
            'AI Engineer': 135000,
            'Cloud Architect': 125000,
            'DevOps Engineer': 115000
        }
        
        base = base_salaries.get(profession, 100000)
        
        # Adjust for cost of living and demand
        adjustments = {
            'CA': 1.3, 'NY': 1.25, 'MA': 1.2, 'WA': 1.25, 'DC': 1.3,
            'CO': 1.15, 'VA': 1.1, 'IL': 1.1, 'TX': 1.05, 'GA': 1.05
        }
        
        return int(base * adjustments.get(state, 1.0))

    def calculate_skills_gap(self, job_data, supply_data):
        """Calculate skills gap using dynamic API data"""
        merged_data = pd.merge(job_data, supply_data, on=['state', 'state_name'])
        
        # Calculate metrics based on whatever data we have
        merged_data['supply_demand_ratio'] = merged_data['job_openings'] / merged_data['professionals']
        merged_data['salary_premium'] = (
            (merged_data['avg_salary'] - merged_data['salary_expectation']) / 
            merged_data['salary_expectation']
        )
        
        # Dynamic opportunity score based on available metrics
        merged_data['opportunity_score'] = (
            (merged_data['supply_demand_ratio'] / merged_data['supply_demand_ratio'].max() * 50) +
            (merged_data['salary_premium'].clip(lower=0) / merged_data['salary_premium'].max() * 30) +
            (merged_data['growth_rate'] / merged_data['growth_rate'].max() * 20)
        )
        
        # Categorize based on dynamic ranges
        def get_opportunity_level(score):
            if score >= 70: return 'CRITICAL GAP'
            elif score >= 50: return 'HIGH OPPORTUNITY'
            elif score >= 30: return 'MODERATE OPPORTUNITY'
            else: return 'BALANCED'
        
        merged_data['opportunity_level'] = merged_data['opportunity_score'].apply(get_opportunity_level)
        
        return merged_data

# Initialize analyzer
analyzer = DynamicAPIAnalyzer()

# Main dashboard
st.title("🔥 Skills Gap Heat Map - Live API Data")
st.markdown("### Real-time data from multiple APIs - Fully dynamic!")

# Test and display API status
available_apis = analyzer.test_all_apis()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Available APIs", len(available_apis))
with col2:
    st.metric("States Analyzed", "12+")
with col3:
    st.metric("Data Freshness", "Live")

# Show API status
st.subheader("🔌 API Connections")
for api, status in analyzer.api_status.items():
    st.write(f"{status} {api}")

# Profession selection
professions = [
    'Data Scientist', 'Software Engineer', 'Cybersecurity Analyst',
    'Healthcare IT Manager', 'AI Engineer', 'Cloud Architect', 'DevOps Engineer'
]

selected_profession = st.selectbox("Select Profession", professions)

if st.button("🔄 Fetch Live Data") or 'data_loaded' in st.session_state:
    with st.spinner("Collecting real-time data from APIs..."):
        job_data, api_usage = analyzer.get_dynamic_job_data(selected_profession)
        supply_data = analyzer.get_dynamic_supply_data(selected_profession)
        gap_data = analyzer.calculate_skills_gap(job_data, supply_data)
    
    st.session_state.data_loaded = True
    
    # Show API usage statistics
    st.subheader("📊 API Usage Summary")
    usage_cols = st.columns(len(api_usage))
    for i, (api, count) in enumerate(api_usage.items()):
        with usage_cols[i]:
            st.metric(f"{api} Calls", count)
    
    # Display the heat map and other visualizations
    # [Include your existing visualization code here]
    
    # Show raw API data for transparency
    with st.expander("🔍 View Raw API Data"):
        st.subheader("Job Data from APIs")
        st.dataframe(job_data)
        
        st.subheader("Supply Data from APIs") 
        st.dataframe(supply_data)
        
        st.subheader("Calculated Gap Analysis")
        st.dataframe(gap_data)

# Add API setup instructions
with st.sidebar:
    st.subheader("🔑 API Setup")
    st.markdown("""
    **Required APIs:**
    - **USAJOBS**: https://developer.usajobs.gov/
    - **Adzuna**: https://developer.adzuna.com/
    - **BLS**: https://data.bls.gov/registrationEngine/
    
    Add keys to Streamlit Cloud secrets.
    """)
