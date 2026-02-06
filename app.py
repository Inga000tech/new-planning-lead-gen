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
    if any(word in applicant for word in ['ltd', 'limited', 'architects', 'developments', 'properties']):
        score += 3
        reasons.append("✓ Company")
    
    # Commercial project (+3)
    if any(word in description for word in ['retail', 'commercial', 'mixed use', 'office', 'shop']):
        score += 3
        reasons.append("✓ Commercial")
    
    # Refused (+2)
    if 'refused' in status:
        score += 2
        reasons.append("✓ Refused")
    
    # Exclude HMO (-5)
    if 'hmo' in description:
        score -= 5
        reasons.append("✗ HMO")
    
    # Exclude extensions (-5)
    if any(word in description for word in ['extension', 'basement', 'loft']):
        score -= 5
        reasons.append("✗ Extension")
    
    # Private homeowner (-2)
    if any(word in applicant for word in ['mr ', 'mrs ', 'miss ', 'ms ']):
        score -= 2
        reasons.append("⚠ Private")
    
    if score >= 5:
        priority = "🟢 A"
    elif score >= 2:
        priority = "🟡 B"
    else:
        priority = "🔴 C"
    
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
        data = response.json()
        return data.get('data', [])
    except:
        return []

# ============================================================================
# MAIN APP
# ============================================================================
st.title("🏗️ Lead Sourcing Engine")
st.markdown("**MA Planning - Qualified Lead Generator**")
st.markdown("---")

# Sidebar
st.sidebar.header("⚙️ Settings")
days = st.sidebar.slider("Days back", 1, 30, 7)
min_score = st.sidebar.slider("Min score", -5, 10, 2)
refused_only = st.sidebar.checkbox("Refused only", True)

if st.sidebar.button("🔍 Search", type="primary"):
    
    with st.spinner("Searching..."):
        apps = get_applications(days)
    
    if not apps:
        st.warning("No applications found")
    else:
        st.success(f"Found {len(apps)} applications")
        
        # Score and filter
        leads = []
        for app in apps:
            score, priority, reasons = score_lead(app)
            
            if score < min_score:
                continue
            
            status = app.get('status_description', '').lower()
            if refused_only and 'refused' not in status:
                continue
            
            leads.append({
                'Priority': priority,
                'Score': score,
                'Address': app.get('site_address', 'N/A'),
                'Applicant': app.get('applicant_name', 'N/A'),
                'Description': app.get('development_description', 'N/A')[:100] + '...',
                'Status': app.get('status_description', 'N/A'),
                'Reference': app.get('planning_application_reference', 'N/A'),
                'Reasons': ' | '.join(reasons)
            })
        
        leads.sort(key=lambda x: x['Score'], reverse=True)
        
        if not leads:
            st.info("No leads match filters")
        else:
            st.subheader(f"📊 {len(leads)} Qualified Leads")
            
            # Display as table
            df = pd.DataFrame(leads)
            st.dataframe(df, use_container_width=True)
            
            # Download
            csv = df.to_csv(index=False)
            st.download_button(
                "📥 Download CSV",
                csv,
                f"leads_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )

else:
    st.info("👈 Configure settings and click Search")
    st.markdown("### Scoring:")
    st.markdown("""
    - ✓ Company (+3)
    - ✓ Commercial (+3)
    - ✓ Refused (+2)
    - ✗ HMO (-5)
    - ✗ Extension (-5)
    - ⚠ Private (-2)
    """)
```

4. Click **"Commit changes"**

**This version:**
- ✅ Much simpler (less likely to break)
- ✅ Same scoring logic
- ✅ Same filters
- ✅ Shows results as a table (easier to read)
- ✅ CSV download still works

**Wait 3-5 minutes** for Streamlit to redeploy.

---

## 🛠️ STEP 4: IF STILL BROKEN - Nuclear Option (Start Fresh)

If it's STILL stuck after both fixes above, let's start completely fresh:

### **Delete and recreate the app:**

1. **Go to Streamlit Cloud:** https://share.streamlit.io/
2. **Click the 3 dots** next to your app → **"Delete app"**
3. **Click "New app"** again
4. Select your repository
5. Make sure it says:
   - Main file: `app.py`
   - Python version: 3.11
6. **Click "Advanced settings"**
7. Add this in "Additional requirements": 
```
   streamlit
   requests
   pandas
