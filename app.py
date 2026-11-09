import streamlit as st

st.set_page_config(
    page_title="Norwegian Energy Data Explorer",
    layout="wide",
)

pages = {
    "Navigation": [
        st.Page("pages/0_home.py", title="Home"),
        st.Page("pages/1_reservoir_measurements.py", title="Reservoir measurements"),
        st.Page("pages/2_reservoir_trends.py", title="Reservoir trends"),
        st.Page("pages/3_reservoir_analysis.py", title="Reservoir analysis"),
        st.Page("pages/4_weather_anomalies.py", title="Weather anomalies"),
        st.Page("pages/5_cross_border_flows.py", title="Cross-border flows"),
        st.Page("pages/6_project_info.py", title="Project information"),
    ]
}

pg = st.navigation(pages)
pg.run()