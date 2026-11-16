import pandas as pd
import streamlit as st

from weather_utils import load_weather_data
from app_utils import load_reservoirs


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.title("Meteorology & Reservoir Correlation")

st.write(
    "Explore the relationship between meteorological conditions "
    "and reservoir levels in Norway."
)

st.info(
    "The analysis is restricted to 2024, as this is the period "
    "for which weather data is available."
)


# --------------------------------------------------
# USER SELECTION
# --------------------------------------------------

zone = st.selectbox(
    "Select electricity zone",
    ["NO1", "NO2", "NO3", "NO4", "NO5"]
)


# --------------------------------------------------
# LOAD WEATHER DATA
# --------------------------------------------------

@st.cache_data
def get_weather_2024(region):
    weather = load_weather_data(region).copy()

    weather["timestamp"] = pd.to_datetime(
        weather["timestamp"],
        utc=True
    )

    weather = weather[
        weather["timestamp"].dt.year == 2024
    ].copy()

    return weather


# --------------------------------------------------
# LOAD RESERVOIR DATA
# --------------------------------------------------

@st.cache_data
def get_reservoirs_2024():
    reservoirs = load_reservoirs().copy()

    reservoirs["date_id"] = pd.to_datetime(
        reservoirs["date_id"]
    )

    reservoirs = reservoirs[
        (reservoirs["area_type"] == "EL")
        & (reservoirs["iso_year"] == 2024)
    ].copy()

    return reservoirs


# --------------------------------------------------
# FILTER DATA FOR SELECTED ZONE
# --------------------------------------------------

try:
    weather_df = get_weather_2024(zone)

    reservoirs_df = get_reservoirs_2024()

    zone_number = int(zone.replace("NO", ""))

    reservoirs_zone = reservoirs_df[
        reservoirs_df["area_number"] == zone_number
    ].copy()

except Exception as error:
    st.error(f"Unable to load data: {error}")
    st.stop()


# --------------------------------------------------
# DISPLAY DATA
# --------------------------------------------------

st.subheader(f"Weather data — {zone}")

st.write(f"Number of weather observations: {len(weather_df)}")
st.dataframe(weather_df.head())

st.subheader(f"Reservoir data — {zone}")

st.write(f"Number of reservoir observations: {len(reservoirs_zone)}")
st.dataframe(reservoirs_zone.head())