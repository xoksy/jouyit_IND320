import streamlit as st

st.set_page_config(
    page_title="Project information",
    layout="wide"
)

st.title("Project information")

st.write(
    "This application explores Norwegian reservoir statistics, "
    "meteorological conditions, and physical electricity flows "
    "between European bidding zones."
)

# --------------------------------------------------
# DATA SOURCES
# --------------------------------------------------

st.header("Data sources")

st.subheader("Reservoir data")

st.write(
    "Reservoir observations are retrieved from the Norwegian Water "
    "Resources and Energy Directorate (NVE) Magasinstatistikk API. "
    "The data includes reservoir filling levels, capacities, and "
    "weekly changes across different Norwegian area types."
)

st.subheader("Weather data")

st.write(
    "Historical meteorological data is retrieved from the Open-Meteo "
    "Historical Weather API using the ERA5 model. The dataset includes "
    "hourly temperature and precipitation "
    "measurements for geographical points across the five Norwegian "
    "electricity zones (NO1–NO5)."
)

st.subheader("Electricity flow data")

st.write(
    "Cross-border physical electricity flow measurements are retrieved "
    "from the ENTSO-E Transparency Platform and stored in the project's "
    "MongoDB database. The data describes electricity exchanges between "
    "European bidding zones."
)

# --------------------------------------------------
# ANALYSIS METHODS
# --------------------------------------------------

st.header("Analysis methods")

st.subheader("Reservoir analysis")

st.write(
    "Reservoir filling levels are studied using two time-series analysis "
    "methods:"
)

st.markdown(
    """
    - **STL decomposition:** separates the observed time series into
      trend, seasonal, and residual components.
    - **Spectrogram:** analyses the frequency content of reservoir
      filling variations over time.
    """
)

st.subheader("Weather anomaly detection")

st.write(
    "Meteorological data is analysed using two anomaly detection methods:"
)

st.markdown(
    """
    - **Precipitation – SPC:** uses Discrete Cosine Transform (DCT)
      high-pass filtering and robust statistical control limits to
      identify unusual precipitation variations.
    - **Temperature – LOF:** uses Local Outlier Factor (LOF) to
      identify unusual temperature observations.
    """
)

# --------------------------------------------------
# HOW TO EXPLORE THE APP
# --------------------------------------------------

st.header("How to explore the app")

st.markdown(
    """
    - **Home:** introduction to the project.
    - **Reservoir measurements:** explore reservoir measurements
      and monthly summaries by area number.
    - **Reservoir trends:** visualize reservoir indicators over
      selected time periods.
    - **Reservoir analysis:** investigate seasonal trends and
      frequency characteristics using STL decomposition
      and spectrograms.
    - **Weather anomalies:** select an electricity zone and
      investigate precipitation and temperature anomalies
      using SPC and LOF.
    - **Cross-border flows:** explore physical electricity
      exchanges between European bidding zones, compare annual
      energy shares, and visualize monthly flow patterns.
    - **Project information:** discover the data sources
      and analytical methods used in this project.
    """
)

# --------------------------------------------------
# PROJECT OBJECTIVE
# --------------------------------------------------

st.header("Project objective")

st.write(
    "The objective of this project is to explore and analyse Norwegian "
    "energy-related data by combining reservoir statistics, meteorological "
    "observations, and cross-border electricity flows. Time-series analysis "
    "and anomaly detection methods are used to identify trends, seasonal "
    "patterns, and unusual observations."
)