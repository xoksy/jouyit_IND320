import streamlit as st

st.title("Norwegian Energy Data Explorer")

st.write(
    """
    Welcome to the Norwegian Energy Data Explorer!

    This application brings together Norwegian reservoir measurements,
    weather observations and cross-border electricity flows. It provides
    tools to explore the data, analyse trends and relationships, and
    generate reservoir filling forecasts.
    """
)

st.divider()

st.header("Explore the application")

st.subheader("1. Data Exploration")

st.markdown(
    """
    - **Reservoir measurements:** browse monthly reservoir measurements
      from the Norwegian Water Resources and Energy Directorate (NVE),
      by area and indicator.
    - **Cross-border flows:** explore physical electricity exchanges
      between Norway and neighbouring European bidding zones, including
      annual energy shares and time-series plots.
    - **Geographical map:** view Norwegian electricity and reservoir areas,
      display reservoir or weather information, and select an area for use
      in other pages.
    """
)

st.subheader("2. Data Analysis")

st.markdown(
    """
    - **Reservoir trends:** visualize the evolution of reservoir indicators
      over time for the area selected on the geographical map.
    - **Reservoir analysis:** investigate seasonal patterns and frequency
      characteristics using STL decomposition and spectrograms.
    """
)

st.subheader("3. Advanced Analytics")

st.markdown(
    """
    - **Weather anomalies:** detect unusual temperature and precipitation
      observations using SATV/SPC and Local Outlier Factor (LOF).
    - **Meteorology & Reservoir Correlation:** study the relationship between
      weekly weather conditions and reservoir indicators, with an adjustable
      time lag. The current analysis uses 2024 data.
    - **Reservoir Forecasting:** predict future reservoir filling levels
      with the SNARIMAX model. Temperature and/or precipitation can also
      be included as additional input variables when weather data is available.
    """
)

st.divider()

st.caption("IND320 Project | Norwegian Energy Data Explorer")
