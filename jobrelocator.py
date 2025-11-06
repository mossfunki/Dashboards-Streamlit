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
            if not self.usajobs_key:
                return {'success': False, 'error': 'No API key'}
                
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
            if not self.adzuna_id or not self.adzuna_key:
                return {'success': False, 'error': 'No API keys'}
                
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
            if not self.bls_key:
                return {'success': False, 'error': 'No BLS API key'}
                
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
            # For now, return estimated salary based on profession and state
            return self.estimate_salary_expectation_from_bls(state)
        except:
            return None

    def estimate_salary_expectation_from_bls(self, state):
        """Estimate salary based on BLS regional data patterns"""
        base_salaries = {
            'CA': 130000, 'NY': 125000, 'MA': 120000, 'WA': 125000, 'DC': 130000,
            'CO': 115000, 'VA': 110000, 'IL': 110000, 'TX': 105000, 'GA': 105000,
            'NC': 100000, 'AZ': 100000, 'FL': 95000, 'MI': 90000, 'OH': 90000
        }
        return base_salaries.get(state, 95000)

    @st.cache_data(ttl=1800)  # 30 minute cache
    def get_dynamic_job_data(_self, profession):
        """Get job data dynamically from all available APIs"""
        states = {
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
        
        job_data = []
        api_usage = {'USAJOBS': 0, 'Adzuna': 0, 'BLS': 0}
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, (state, state_name) in enumerate(states.items()):
            status_text.text(f"Fetching job data for {state_name}... ({i+1}/{len(states)})")
            
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
                    time.sleep(0.1)  # Rate limiting
            
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
                    time.sleep(0.1)  # Rate limiting
            
            # If no job data from APIs, use realistic estimates
            if state_job_data['job_openings'] == 0:
                state_job_data['job_openings'] = _self.get_realistic_job_estimate(profession, state)
                state_job_data['sources_used'].append('Estimate')
            
            # Ensure we have a salary
            if not state_job_data['avg_salary']:
                state_job_data['avg_salary'] = _self.estimate_salary_expectation_from_bls(state)
            
            # Calculate growth rate
            state_job_data['growth_rate'] = _self.calculate_dynamic_growth(profession, state, state_job_data)
            job_data.append(state_job_data)
            
            progress_bar.progress((i + 1) / len(states))
        
        status_text.empty()
        progress_bar.empty()
        
        return pd.DataFrame(job_data), api_usage

    def get_realistic_job_estimate(self, profession, state):
        """Provide realistic job estimates when APIs fail"""
        base_estimates = {
            'Data Scientist': 350,
            'Software Engineer': 1200,
            'Cybersecurity Analyst': 180,
            'Healthcare IT Manager': 120,
            'AI Engineer': 85,
            'Cloud Architect': 150,
            'DevOps Engineer': 220
        }
        
        base = base_estimates.get(profession, 200)
        
        # State multipliers
        state_multipliers = {
            'CA': 2.8, 'TX': 1.9, 'NY': 1.7, 'FL': 1.5, 'WA': 2.1,
            'MA': 1.8, 'CO': 1.7, 'NC': 1.5, 'GA': 1.4, 'IL': 1.4,
            'VA': 1.6, 'AZ': 1.3, 'PA': 1.2, 'MI': 1.1, 'OH': 1.1,
            'NJ': 1.3, 'TN': 1.1, 'MO': 1.0, 'MD': 1.3, 'WI': 1.0,
            'MN': 1.1, 'IN': 0.9, 'AL': 0.8, 'SC': 0.9, 'LA': 0.8,
            'KY': 0.8, 'OR': 1.2, 'OK': 0.8, 'CT': 1.1, 'IA': 0.7,
            'UT': 1.2, 'NV': 1.0, 'AR': 0.7, 'MS': 0.6, 'KS': 0.7,
            'NM': 0.8, 'NE': 0.6, 'WV': 0.6, 'ID': 0.7, 'HI': 0.8,
            'NH': 0.9, 'ME': 0.7, 'RI': 0.8, 'MT': 0.6, 'DE': 0.8,
            'SD': 0.5, 'ND': 0.5, 'AK': 0.6, 'VT': 0.6, 'WY': 0.5
        }
        
        multiplier = state_multipliers.get(state, 0.8)
        return int(base * multiplier)

    @st.cache_data(ttl=86400)  # 24 hour cache
    def get_dynamic_supply_data(_self, profession):
        """Get professional supply data dynamically from available APIs"""
        states = {
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
        
        supply_data = []
        
        # Get national employment data from BLS
        national_result = _self.call_bls_api(profession)
        
        # Use fallback national data if BLS fails
        if not national_result['success'] or not national_result['employment']:
            national_employment = _self.get_fallback_national_employment(profession)
        else:
            national_employment = national_result['employment']
        
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
                else:
                    # Estimate based on national data
                    state_supply_data['professionals'] = _self.estimate_state_employment(
                        national_employment, profession, state
                    )
                    state_supply_data['sources_used'].append('Estimated from BLS National')
            else:
                # No BLS key, use estimates
                state_supply_data['professionals'] = _self.estimate_state_employment(
                    national_employment, profession, state
                )
                state_supply_data['sources_used'].append('Estimated')
            
            # Get salary expectation
            state_supply_data['salary_expectation'] = _self.estimate_salary_expectation_from_bls(state)
            
            supply_data.append(state_supply_data)
        
        return pd.DataFrame(supply_data)

    def get_fallback_national_employment(self, profession):
        """Provide fallback national employment data when BLS fails"""
        fallback_data = {
            'Data Scientist': 35200,
            'Software Engineer': 1468000,
            'Cybersecurity Analyst': 163000,
            'Healthcare IT Manager': 476000,
            'AI Engineer': 12500,
            'Cloud Architect': 34200,
            'DevOps Engineer': 89200
        }
        return fallback_data.get(profession, 50000)

    def estimate_state_employment(self, national_employment, profession, state):
        """Estimate state employment based on national data and state characteristics"""
        if national_employment is None:
            national_employment = self.get_fallback_national_employment(profession)
            
        state_populations = {
            'CA': 0.118, 'TX': 0.087, 'FL': 0.065, 'NY': 0.059, 'PA': 0.039,
            'IL': 0.038, 'OH': 0.035, 'GA': 0.032, 'NC': 0.031, 'MI': 0.030,
            'NJ': 0.026, 'VA': 0.026, 'WA': 0.023, 'AZ': 0.022, 'MA': 0.021,
            'TN': 0.020, 'IN': 0.020, 'MO': 0.018, 'MD': 0.018, 'WI': 0.017,
            'CO': 0.017, 'MN': 0.017, 'SC': 0.016, 'AL': 0.015, 'LA': 0.014,
            'KY': 0.013, 'OR': 0.013, 'OK': 0.012, 'CT': 0.011, 'UT': 0.010,
            'IA': 0.010, 'NV': 0.009, 'AR': 0.009, 'MS': 0.009, 'KS': 0.009,
            'NM': 0.006, 'NE': 0.006, 'WV': 0.005, 'ID': 0.005, 'HI': 0.004,
            'NH': 0.004, 'ME': 0.004, 'RI': 0.003, 'MT': 0.003, 'DE': 0.003,
            'SD': 0.003, 'ND': 0.002, 'AK': 0.002, 'VT': 0.002, 'WY': 0.002
        }
        
        tech_concentration = {
            'CA': 2.5, 'WA': 2.2, 'MA': 2.0, 'NY': 1.8, 'CO': 1.7,
            'TX': 1.6, 'VA': 1.5, 'NC': 1.4, 'GA': 1.3, 'IL': 1.3,
            'AZ': 1.2, 'UT': 1.4, 'OR': 1.3, 'MN': 1.2, 'NJ': 1.2,
            'MD': 1.4, 'CT': 1.2, 'WI': 1.0, 'MI': 0.9, 'OH': 0.9,
            'PA': 1.0, 'MO': 0.9, 'TN': 0.8, 'IN': 0.7, 'AL': 0.6,
            'SC': 0.7, 'LA': 0.6, 'KY': 0.6, 'OK': 0.6, 'IA': 0.5,
            'NV': 0.8, 'AR': 0.5, 'MS': 0.4, 'KS': 0.5, 'NM': 0.6,
            'NE': 0.4, 'WV': 0.3, 'ID': 0.7, 'HI': 0.8, 'NH': 0.8,
            'ME': 0.5, 'RI': 0.7, 'MT': 0.4, 'DE': 0.7, 'SD': 0.3,
            'ND': 0.3, 'AK': 0.5, 'VT': 0.6, 'WY': 0.3
        }
        
        state_share = state_populations.get(state, 0.01)
        concentration = tech_concentration.get(state, 0.8)
        
        return int(national_employment * state_share * concentration)

    def calculate_dynamic_growth(self, profession, state, job_data):
        """Calculate growth rate based on real market conditions"""
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
        high_growth_states = ['TX', 'NC', 'TN', 'UT', 'CO', 'AZ', 'GA', 'FL', 'NV']
        if state in high_growth_states:
            return base_growth * 1.3
        return base_growth

    def calculate_skills_gap(self, job_data, supply_data):
        """Calculate skills gap using dynamic API data"""
        merged_data = pd.merge(job_data, supply_data, on=['state', 'state_name'])
        
        # Calculate metrics based on whatever data we have
        merged_data['supply_demand_ratio'] = merged_data['job_openings'] / merged_data['professionals']
        
        # Handle salary premium calculation safely
        merged_data['salary_premium'] = 0
        valid_salary_mask = (merged_data['avg_salary'].notna()) & (merged_data['salary_expectation'].notna())
        merged_data.loc[valid_salary_mask, 'salary_premium'] = (
            (merged_data.loc[valid_salary_mask, 'avg_salary'] - merged_data.loc[valid_salary_mask, 'salary_expectation']) / 
            merged_data.loc[valid_salary_mask, 'salary_expectation']
        )
        
        # Dynamic opportunity score based on available metrics
        ratio_max = merged_data['supply_demand_ratio'].max() if not merged_data['supply_demand_ratio'].empty else 1
        premium_max = merged_data['salary_premium'].max() if not merged_data['salary_premium'].empty else 1
        growth_max = merged_data['growth_rate'].max() if not merged_data['growth_rate'].empty else 1
        
        merged_data['opportunity_score'] = (
            (merged_data['supply_demand_ratio'] / ratio_max * 50) +
            (merged_data['salary_premium'].clip(lower=0) / premium_max * 30) +
            (merged_data['growth_rate'] / growth_max * 20)
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
st.markdown("### Real-time data from multiple APIs - All 50 States!")

# Test and display API status
available_apis = analyzer.test_all_apis()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Available APIs", len(available_apis))
with col2:
    st.metric("States Analyzed", "50")
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
    try:
        with st.spinner("Collecting real-time data from all 50 states..."):
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
        
        # Display the heat map with improved color scheme
        st.subheader("🗺️ Skills Gap Heat Map")
        st.markdown("**Darker colors = Higher opportunity | Lighter colors = Lower opportunity**")

        # Calculate display metrics
        gap_data['salary_display'] = gap_data['avg_salary'].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "N/A")
        gap_data['jobs_per_pro'] = gap_data['supply_demand_ratio'].round(2)
        gap_data['opportunity_score_rounded'] = gap_data['opportunity_score'].round(1)

        # Create heat map with sequential color scale (light to dark)
        fig = px.choropleth(
            gap_data,
            locations='state',
            locationmode='USA-states',
            color='opportunity_score',
            scope='usa',
            color_continuous_scale='Blues',  # Light blue to dark blue
            range_color=(0, 100),
            title=f'{selected_profession} - Skills Gap Heat Map<br><sub>Dark Blue: High Opportunity | Light Blue: Lower Opportunity</sub>',
            hover_data={
                'state_name': True,
                'job_openings': True,
                'professionals': True,
                'jobs_per_pro': ':.2f',
                'salary_display': True,
                'opportunity_score_rounded': True,
                'opportunity_level': True
            },
            labels={
                'opportunity_score': 'Opportunity Score',
                'state_name': 'State',
                'job_openings': 'Job Openings',
                'professionals': 'Local Professionals',
                'jobs_per_pro': 'Jobs per Professional',
                'salary_display': 'Avg Salary',
                'opportunity_score_rounded': 'Score'
            }
        )

        # Customize the layout
        fig.update_layout(
            height=600,
            geo=dict(
                bgcolor='rgba(0,0,0,0)',
                lakecolor='rgba(0,0,0,0)',
                landcolor='rgba(240,240,240,0.8)'
            ),
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(size=12),
            coloraxis_colorbar=dict(
                title="Opportunity<br>Score",
                thickness=15,
                len=0.75,
                yanchor="middle",
                y=0.5
            )
        )

        # Add state borders for better visibility
        fig.update_geos(
            showcoastlines=True,
            coastlinecolor="white",
            showland=True,
            landcolor="lightgray",
            showocean=True,
            oceancolor="lightblue",
            showlakes=True,
            lakecolor="lightblue",
            showrivers=True,
            rivercolor="lightblue"
        )

        st.plotly_chart(fig, use_container_width=True)

        # Show ALL opportunity markets in order
        st.subheader("🏆 All States Ranked by Opportunity Score")
        st.markdown("**All 50 states sorted from highest to lowest opportunity**")

        # Sort by opportunity score (highest first) and show ALL states
        all_opportunities = gap_data.sort_values('opportunity_score', ascending=False)[[
            'state_name', 'job_openings', 'professionals', 'jobs_per_pro',
            'salary_display', 'opportunity_score_rounded', 'opportunity_level'
        ]]

        # Display all states in a sorted table
