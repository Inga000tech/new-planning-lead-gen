import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import time

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="Mark's Lead Sourcing Engine",
    page_icon="🏗️",
    layout="wide"
)

# ============================================================================
# COUNCIL CONFIGURATIONS
# ============================================================================
COUNCILS = {
    "London Planning Datahub": {
        "url": "https://planningdata.london.gov.uk/api-guest/applications",
        "type": "london_api",
        "params_template": {
            "date_received_start": None,  # Will be filled dynamically
            "date_received_end": None,
            "work_type": "change_of_use",
            "page_size": 100
        }
    },
    "Southwark": {
        "url": "https://planning.southwark.gov.uk/online-applications/search.do",
        "type": "idox_search",
        "search_type": "Application"
    }
}

# ============================================================================
# SCORING LOGIC (Mark's Criteria)
# ============================================================================
def score_lead(application):
    """
    Score each lead based on Mark's business criteria
    Returns: (score, priority_label, reasons)
    """
    score = 0
    reasons = []
    
    # Get fields (handle different API formats)
    applicant = str(application.get('applicant', application.get('applicant_name', ''))).lower()
    description = str(application.get('description', application.get('proposal', ''))).lower()
    status = str(application.get('status', application.get('decision', ''))).lower()
    
    # ========== POSITIVE SCORING ==========
    
    # 1. APPLICANT TYPE (+3 points for companies)
    company_keywords = ['ltd', 'limited', 'architects', 'developments', 'properties', 'consulting', 'design']
    if any(keyword in applicant for keyword in company_keywords):
        score += 3
        reasons.append("✓ Company applicant")
    
    # 2. PROJECT TYPE (+3 points for retail/commercial)
    commercial_keywords = ['retail', 'commercial', 'mixed use', 'office', 'shop', 'restaurant', 'cafe']
    if any(keyword in description for keyword in commercial_keywords):
        score += 3
        reasons.append("✓ Commercial/Mixed-use project")
    
    # 3. REFUSAL STATUS (+2 points)
    if 'refused' in status or 'reject' in status:
        score += 2
        reasons.append("✓ Recently refused (appeal opportunity)")
    
    # 4. PRIOR APPROVAL / CHANGE OF USE (+1 point)
    if 'prior approval' in description or 'change of use' in description:
        score += 1
        reasons.append("✓ Prior Approval/Change of Use")
    
    # ========== NEGATIVE SCORING ==========
    
    # 5. EXCLUDE HMOs (-5 points)
    if 'hmo' in description or 'house in multiple occupation' in description or 'house of multiple occupation' in description:
        score -= 5
        reasons.append("✗ HMO (excluded)")
    
    # 6. EXCLUDE LARGE EXTENSIONS (-5 points)
    extension_keywords = ['extension', 'basement', 'loft conversion', 'rear extension', 'side extension']
    if any(keyword in description for keyword in extension_keywords):
        score -= 5
        reasons.append("✗ Extension/Loft (excluded)")
    
    # 7. PRIVATE HOMEOWNER (-2 points)
    private_keywords = ['mr ', 'mrs ', 'miss ', 'ms ', 'dr ']
    if any(keyword in applicant for keyword in private_keywords):
        score -= 2
        reasons.append("⚠ Private homeowner")
    
    # ========== PRIORITY LABEL ==========
    if score >= 5:
        priority = "🟢 A - HIGH PRIORITY"
    elif score >= 2:
        priority = "🟡 B - MEDIUM"
    else:
        priority = "🔴 C - LOW"
    
    return score, priority, reasons


# ============================================================================
# SCRAPING FUNCTIONS
# ============================================================================

def scrape_london_datahub(days_back=7):
    """Scrape London Planning Datahub API"""
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    url = COUNCILS["London Planning Datahub"]["url"]
    params = {
        "date_received_start": start_date.strftime("%Y-%m-%d"),
        "date_received_end": end_date.strftime("%Y-%m-%d"),
        "page_size": 100
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        applications = []
        for app in data.get('data', []):
            applications.append({
                'council': 'London Datahub',
                'reference': app.get('planning_application_reference', 'N/A'),
                'address': app.get('site_address', 'N/A'),
                'description': app.get('development_description', 'N/A'),
                'applicant': app.get('applicant_name', 'N/A'),
                'status': app.get('status_description', 'N/A'),
                'date': app.get('date_received', 'N/A'),
                'link': f"https://planningdata.london.gov.uk/planning-application/{app.get('planning_application_reference', '')}"
            })
        
        return applications
    
    except Exception as e:
        st.error(f"Error scraping London Datahub: {str(e)}")
        return []


def scrape_southwark(days_back=7):
    """Scrape Southwark Council (simplified - returns placeholder)"""
    
    # Note: Southwark requires more complex scraping with BeautifulSoup
    # For now, returning empty list - we can add full implementation if needed
    st.info("Southwark scraping requires additional setup. Focus on London Datahub for now.")
    return []


# ============================================================================
# MAIN APP
# ============================================================================

def main():
    
    # ========== HEADER ==========
    st.title("🏗️ Lead Sourcing Engine for MA Planning")
    st.markdown("**Automated lead generation for Urban Planning consultancy**")
    st.markdown("---")
    
    # ========== SIDEBAR CONTROLS ==========
    st.sidebar.header("⚙️ Search Settings")
    
    # Council selector
    selected_councils = st.sidebar.multiselect(
        "Select Councils to Search:",
        options=list(COUNCILS.keys()),
        default=["London Planning Datahub"]
    )
    
    # Date range
    days_back = st.sidebar.slider(
        "Days to look back:",
        min_value=1,
        max_value=30,
        value=7,
        help="How many days of planning applications to search"
    )
    
    # Minimum score filter
    min_score = st.sidebar.slider(
        "Minimum Priority Score:",
        min_value=-5,
        max_value=10,
        value=2,
        help="Only show leads scoring above this threshold"
    )
    
    # Show refused only toggle
    refused_only = st.sidebar.checkbox(
        "Show Refused Applications Only",
        value=True,
        help="Filter for appeal opportunities"
    )
    
    # Search button
    search_button = st.sidebar.button("🔍 Search for Leads", type="primary")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Quick Stats:**")
    st.sidebar.info("Target: 6 qualified leads/month\nAvg Fee: £2,000\nConversion: ~50%")
    
    # ========== MAIN CONTENT AREA ==========
    
    if search_button:
        
        if not selected_councils:
            st.warning("⚠️ Please select at least one council to search.")
            return
        
        all_applications = []
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Scrape each selected council
        for idx, council in enumerate(selected_councils):
            status_text.text(f"Searching {council}...")
            
            if council == "London Planning Datahub":
                apps = scrape_london_datahub(days_back)
                all_applications.extend(apps)
            elif council == "Southwark":
                apps = scrape_southwark(days_back)
                all_applications.extend(apps)
            
            progress_bar.progress((idx + 1) / len(selected_councils))
            time.sleep(0.5)
        
        progress_bar.empty()
        status_text.empty()
        
        # ========== SCORING & FILTERING ==========
        
        if not all_applications:
            st.warning("No applications found for the selected criteria.")
            return
        
        st.success(f"✅ Found {len(all_applications)} applications. Analyzing...")
        
        # Score each application
        scored_leads = []
        for app in all_applications:
            score, priority, reasons = score_lead(app)
            
            # Apply filters
            if score < min_score:
                continue
            
            if refused_only and 'refused' not in app['status'].lower():
                continue
            
            scored_leads.append({
                **app,
                'score': score,
                'priority': priority,
                'reasons': ' | '.join(reasons)
            })
        
        # Sort by score (highest first)
        scored_leads.sort(key=lambda x: x['score'], reverse=True)
        
        # ========== DISPLAY RESULTS ==========
        
        st.markdown("---")
        st.subheader(f"📊 Found {len(scored_leads)} Qualified Leads")
        
        if len(scored_leads) == 0:
            st.info("No leads match your current filters. Try lowering the minimum score or expanding the date range.")
            return
        
        # Display each lead
        for idx, lead in enumerate(scored_leads, 1):
            
            # Color-coded container based on priority
            if "🟢 A" in lead['priority']:
                container = st.container(border=True)
                with container:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"### {idx}. {lead['priority']}")
                    with col2:
                        st.metric("Score", lead['score'])
            else:
                with st.expander(f"{idx}. {lead['priority']} - {lead['address'][:50]}...", expanded=False):
                    container = st.container()
            
            with container:
                # Lead details
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**Address:** {lead['address']}")
                    st.markdown(f"**Applicant:** {lead['applicant']}")
                    st.markdown(f"**Description:** {lead['description'][:200]}...")
                    st.markdown(f"**Status:** {lead['status']}")
                    st.markdown(f"**Date:** {lead['date']}")
                
                with col2:
                    st.markdown("**Scoring Breakdown:**")
                    st.caption(lead['reasons'])
                    
                    # Action buttons
                    st.link_button("📄 View Application", lead['link'])
                    
                    # Contact research link
                    search_query = f"{lead['applicant']} UK contact architect developer"
                    google_search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
                    st.link_button("🔍 Research Contact", google_search_url)
                
                st.markdown("---")
        
        # ========== EXPORT OPTION ==========
        
        st.subheader("📥 Export Leads")
        
        # Convert to DataFrame for export
        export_df = pd.DataFrame(scored_leads)
        csv = export_df.to_csv(index=False)
        
        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name=f"leads_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    else:
        # ========== WELCOME SCREEN ==========
        st.info("👈 Select councils and click 'Search for Leads' to start")
        
        st.markdown("### How it works:")
        st.markdown("""
        1. **Select councils** from the sidebar (start with London Planning Datahub)
        2. **Set date range** (default: last 7 days)
        3. **Adjust filters** (minimum score, refused only)
        4. **Click Search** to find qualified leads
        5. **Review results** - prioritized A/B/C based on Mark's criteria
        6. **Export** top leads to CSV for follow-up
        """)
        
        st.markdown("### Scoring Criteria:")
        st.markdown("""
        **Positive signals:**
        - ✓ Company applicant (+3)
        - ✓ Commercial/Mixed-use project (+3)
        - ✓ Refused status (+2)
        - ✓ Prior Approval/Change of Use (+1)
        
        **Negative signals:**
        - ✗ HMO (-5)
        - ✗ Extensions/Basements (-5)
        - ⚠ Private homeowner (-2)
        """)


if __name__ == "__main__":
    main()
