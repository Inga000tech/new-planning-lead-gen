import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(
    page_title="Mark's Lead Sourcing Engine",
    page_icon="🏗️",
    layout="wide"
)

# ============================================================================
# SCORING LOGIC
# ============================================================================
def score_lead(application):
    score = 0
    reasons = []
    
    applicant = str(application.get('applicant_name', '')).lower()
    description = str(application.get('development_description', '')).lower()
    status = str(application.get('status_description', '')).lower()
    
    # Company applicant (+3)
    if any(word in applicant for word in ['ltd', 'limited', 'architects', 'developments', 'properties', 'consulting', 'design']):
        score += 3
        reasons.append("Company applicant")
    
    # Commercial project (+3)
    if any(word in description for word in ['retail', 'commercial', 'mixed use', 'office', 'shop', 'restaurant', 'cafe']):
        score += 3
        reasons.append("Commercial project")
    
    # Refused (+2)
    if 'refused' in status or 'reject' in status:
        score += 2
        reasons.append("Refused (appeal opportunity)")
    
    # Prior approval (+1)
    if 'prior approval' in description or 'change of use' in description:
        score += 1
        reasons.append("Prior Approval/Change of Use")
    
    # Exclude HMO (-5)
    if 'hmo' in description or 'house in multiple occupation' in description:
        score -= 5
        reasons.append("HMO (excluded)")
    
    # Exclude extensions (-5)
    if any(word in description for word in ['extension', 'basement', 'loft conversion', 'rear extension', 'side extension']):
        score -= 5
        reasons.append("Extension/Basement (excluded)")
    
    # Private homeowner (-2)
    if any(word in applicant for word in ['mr ', 'mrs ', 'miss ', 'ms ', 'dr ']):
        score -= 2
        reasons.append("Private homeowner")
    
    if score >= 5:
        priority = "A - HIGH"
    elif score >= 2:
        priority = "B - MEDIUM"
    else:
        priority = "C - LOW"
    
    return score, priority, reasons

# ============================================================================
# FETCH DATA
# ============================================================================
def get_applications(days_back=7):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    url = "https://planningdata.london.gov.uk/api-guest/applications"
    params = {
        "date_received_start": start_date.strftime("%Y-%m-%d"),
        "date_received_end": end_date.strftime("%Y-%m-%d"),
        "page_size": 100
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get('data', [])
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return []

# ============================================================================
# MAIN APP
# ============================================================================
st.title("🏗️ Lead Sourcing Engine for MA Planning")
st.markdown("**Automated qualified lead generation for Urban Planning consultancy**")
st.markdown("---")

# Sidebar controls
st.sidebar.header("⚙️ Search Settings")

days = st.sidebar.slider("Days to look back:", 1, 30, 7)
min_score = st.sidebar.slider("Minimum score:", -5, 10, 2)
refused_only = st.sidebar.checkbox("Refused applications only", True)

st.sidebar.markdown("---")
st.sidebar.markdown("**Business Goals:**")
st.sidebar.info("Target: 6 leads/month\nAvg Fee: £2,000\nConversion: 50%")

search_button = st.sidebar.button("🔍 Search for Leads", type="primary")

# Main content
if search_button:
    
    with st.spinner("Searching London Planning Datahub..."):
        apps = get_applications(days)
    
    if not apps:
        st.warning("No applications found for the selected date range.")
    else:
        st.success(f"Found {len(apps)} applications. Analyzing...")
        
        # Score and filter
        leads = []
        for app in apps:
            score, priority, reasons = score_lead(app)
            
            # Apply filters
            if score < min_score:
                continue
            
            status = app.get('status_description', '').lower()
            if refused_only and 'refused' not in status:
                continue
            
            # Build contact research URL
            applicant_name = app.get('applicant_name', 'N/A')
            search_query = f"{applicant_name} UK contact architect developer".replace(' ', '+')
            research_url = f"https://www.google.com/search?q={search_query}"
            
            # Build application URL
            ref = app.get('planning_application_reference', '')
            app_url = f"https://planningdata.london.gov.uk/planning-application/{ref}"
            
            leads.append({
                'Priority': priority,
                'Score': score,
                'Address': app.get('site_address', 'N/A'),
                'Applicant': applicant_name,
                'Description': app.get('development_description', 'N/A')[:150] + '...',
                'Status': app.get('status_description', 'N/A'),
                'Date': app.get('date_received', 'N/A'),
                'Reference': ref,
                'Why scored high': ' | '.join(reasons),
                'Application Link': app_url,
                'Research Link': research_url
            })
        
        # Sort by score
        leads.sort(key=lambda x: x['Score'], reverse=True)
        
        if not leads:
            st.info("No leads match your current filters. Try lowering the minimum score or expanding the date range.")
        else:
            st.subheader(f"📊 Found {len(leads)} Qualified Leads")
            
            # Display leads
            for idx, lead in enumerate(leads, 1):
                
                # Color based on priority
                if lead['Priority'] == "A - HIGH":
                    with st.container(border=True):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"### {idx}. 🟢 {lead['Priority']}")
                        with col2:
                            st.metric("Score", lead['Score'])
                        
                        st.markdown(f"**Address:** {lead['Address']}")
                        st.markdown(f"**Applicant:** {lead['Applicant']}")
                        st.markdown(f"**Description:** {lead['Description']}")
                        st.markdown(f"**Status:** {lead['Status']}")
                        st.markdown(f"**Date:** {lead['Date']}")
                        st.caption(f"**Scoring:** {lead['Why scored high']}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.link_button("📄 View Application", lead['Application Link'])
                        with col2:
                            st.link_button("🔍 Research Contact", lead['Research Link'])
                
                else:
                    emoji = "🟡" if lead['Priority'] == "B - MEDIUM" else "🔴"
                    with st.expander(f"{idx}. {emoji} {lead['Priority']} - {lead['Address'][:60]}...", expanded=False):
                        st.markdown(f"**Applicant:** {lead['Applicant']}")
                        st.markdown(f"**Description:** {lead['Description']}")
                        st.markdown(f"**Status:** {lead['Status']}")
                        st.markdown(f"**Date:** {lead['Date']}")
                        st.caption(f"**Scoring:** {lead['Why scored high']}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.link_button("📄 View Application", lead['Application Link'])
                        with col2:
                            st.link_button("🔍 Research Contact", lead['Research Link'])
            
            st.markdown("---")
            
            # Export to CSV
            st.subheader("📥 Export Leads")
            df = pd.DataFrame(leads)
            csv = df.to_csv(index=False)
            
            st.download_button(
                label="Download as CSV",
                data=csv,
                file_name=f"leads_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

else:
    # Welcome screen
    st.info("👈 Configure your search settings in the sidebar and click 'Search for Leads'")
    
    st.markdown("### How it works:")
    st.markdown("""
    1. Select date range (default: last 7 days)
    2. Set minimum priority score
    3. Choose to filter refused applications only
    4. Click 'Search for Leads'
    5. Review results prioritized A/B/C
    6. Export to CSV for tracking
    """)
    
    st.markdown("### Scoring System:")
    st.markdown("""
    **Positive signals:**
    - Company applicant (+3)
    - Commercial/Mixed-use project (+3)
    - Refused status (+2)
    - Prior Approval/Change of Use (+1)
    
    **Negative signals:**
    - HMO (-5)
    - Extensions/Basements (-5)
    - Private homeowner (-2)
    
    **Priority levels:**
    - A (High): Score 5+
    - B (Medium): Score 2-4
    - C (Low): Score below 2
    """)
