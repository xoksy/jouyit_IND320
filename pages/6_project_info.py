import streamlit as st

st.set_page_config(
    page_title="Project information",
    layout="wide"
)

st.title("Project information")

st.write(
    """
    The Norwegian Energy Data Explorer is an IND320 project that brings
    together Norwegian reservoir statistics, meteorological observations
    and cross-border electricity flows. It combines data exploration,
    time-series analysis, anomaly detection and reservoir forecasting.
    """
)

st.divider()

# --------------------------------------------------
# PROJECT OBJECTIVE
# --------------------------------------------------

st.header("Project overview")

st.write(
    """
    The objective is to explore Norwegian energy-related data and investigate
    how reservoir conditions, weather and electricity exchanges evolve over
    time. The application provides interactive visualizations and analytical
    tools to help identify trends, seasonal patterns, unusual observations
    and possible relationships between variables.
    """
)

# --------------------------------------------------
# DATA SOURCES AND STORAGE
# --------------------------------------------------

st.header("Data sources and storage")

st.subheader("Reservoir data")

st.write(
    """
    Reservoir measurements are retrieved from the Norwegian Water Resources
    and Energy Directorate (NVE) Magasinstatistikk API. They include indicators
    such as filling degree, filling volume, capacity and changes in reservoir
    levels across Norwegian geographical areas.
    """
)

st.subheader("Weather data")

st.write(
    """
    Historical meteorological observations are sourced from the Open-Meteo
    Historical Weather API using the ERA5 dataset. The data includes hourly
    temperature and precipitation observations for geographical points in
    the five Norwegian electricity zones (NO1–NO5). The analyses currently
    focus on 2024, the period available in the project dataset.
    """
)

st.subheader("Cross-border electricity flows")

st.write(
    """
    Physical electricity flow measurements are retrieved from the ENTSO-E
    Transparency Platform. The project stores these records in MongoDB and
    uses them to explore exchanges between Norway and neighbouring European
    bidding zones. Power is expressed in MW; energy totals are estimated
    in MWh by taking the duration between consecutive measurements into account.
    """
)

st.caption(
    "Reservoir measurements are retrieved from the NVE API, while the "
    "weather and cross-border flow datasets are accessed through the "
    "project's data-loading utilities."
)

# --------------------------------------------------
# ANALYSIS METHODS
# --------------------------------------------------

st.divider()
st.header("Analysis methods")

st.subheader("Reservoir trends and time-series analysis")

st.markdown(
    """
    - **Reservoir trends:** visualizes the evolution of selected reservoir
      indicators over time for the geographical area selected by the user.
    - **STL decomposition:** separates a time series into trend, seasonal
      and residual components.
    - **Spectrogram:** examines how the frequency content of reservoir
      filling variations changes over time.
    """
)

st.subheader("Weather anomaly detection")

st.markdown(
    """
    - **SATV / SPC:** applies Discrete Cosine Transform (DCT) high-pass
      filtering and robust statistical control limits to identify unusual
      weather observations.
    - **Local Outlier Factor (LOF):** identifies observations that are
      unusual compared with their local neighbourhood.
    """
)

st.write(
    "Both anomaly detection approaches can be applied to the weather "
    "properties offered by the application: temperature and precipitation."
)

# --------------------------------------------------
# ADVANCED ANALYTICS
# --------------------------------------------------

st.divider()
st.header("Advanced analytics")

st.subheader("Meteorology & Reservoir Correlation")

st.write(
    """
    This page compares weekly weather observations with weekly reservoir
    indicators for a selected electricity zone. It calculates the Pearson
    correlation coefficient and allows a time lag to be applied to the
    weather variable, making it possible to investigate whether earlier
    weather conditions are associated with later changes in reservoir levels.
    The current analysis uses data from 2024.
    """
)

st.subheader("Reservoir forecasting")

st.write(
    """
    Reservoir filling levels are forecast using the SNARIMAX model from
    the River library. The user can select the forecast horizon and adjust
    the model parameters. Temperature and precipitation can also be selected
    as exogenous input variables when generating a weather-based forecast.
    """
)

st.info(
    "Weather-based forecasting is currently limited by the availability "
    "of weather observations for 2024. Future weather inputs are based on "
    "the corresponding 2024 weekly observations, so they represent a "
    "reference-weather scenario rather than an independent weather forecast."
)

st.divider()

st.caption("IND320 Project | Norwegian Energy Data Explorer")
