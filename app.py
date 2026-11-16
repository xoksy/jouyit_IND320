import streamlit as st

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Norwegian Energy Data Explorer",
    page_icon="⚡",
    layout="wide"
)

# Shared selections across pages
if "shared_area_type" not in st.session_state:
    st.session_state.shared_area_type = "EL"

if "shared_area_number" not in st.session_state:
    st.session_state.shared_area_number = 1

# --------------------------------------------------
# NAVIGATION STRUCTURE
# --------------------------------------------------

pages = {
    "Home": [
        st.Page("pages/0_home.py", title="Home", icon="🏠", default=True)
    ],

    "Data Exploration": [
        st.Page("pages/1_reservoir_measurements.py", title="Reservoir measurements", icon="💧"),
        st.Page("pages/5_cross_border_flows.py", title="Cross-border flows", icon="⚡"),
        st.Page("pages/7_geographical_map.py",    title="Geographical map", icon="🗺️")
    ],

    "Data Analysis": [
        st.Page("pages/2_reservoir_trends.py", title="Reservoir trends", icon="📈"),
        st.Page("pages/3_reservoir_analysis.py", title="Reservoir analysis", icon="🔬")
    ],

    "Advanced Analytics": [
        st.Page("pages/4_weather_anomalies.py", title="Weather anomalies", icon="🌦️")
    ],

    "About": [
        st.Page("pages/6_project_info.py", title="Project information", icon="ℹ️")
    ]
}

# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------

pg = st.navigation(pages, position="sidebar")
pg.run()