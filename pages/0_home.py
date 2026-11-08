import streamlit as st

st.title("Norwegian Energy Data Explorer")

st.write(
    """
    Welcome to the Norwegian Energy Data Explorer!

    This application provides an interactive exploration of Norwegian
    energy-related data by combining reservoir statistics, meteorological
    observations, and cross-border electricity flows.
    """
)

st.header("Explore the application")

st.subheader("Reservoir data")

st.write(
    """
    Explore Norwegian reservoir statistics through historical measurements,
    time-series visualizations, and advanced analyses.
    
    Available methods include STL decomposition and spectrogram analysis
    to investigate seasonal patterns and frequency characteristics.
    """
)

st.subheader("Weather data")

st.write(
    """
    Investigate meteorological conditions across the five Norwegian
    electricity zones (NO1–NO5). Explore hourly temperature and
    precipitation measurements and identify unusual observations
    using SPC and Local Outlier Factor (LOF).
    """
)

st.subheader("Cross-border electricity flows")

st.write(
    """
    Explore physical electricity exchanges between Norwegian and
    neighbouring European bidding zones. Compare annual energy
    distributions and visualize electricity flow variations over time.
    """
)

st.divider()

st.caption(
    "IND320 Project | Norwegian Energy Data Analysis"
)