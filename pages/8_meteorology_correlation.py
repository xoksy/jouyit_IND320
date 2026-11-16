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

def aggregate_weather_weekly(weather):
    weather = weather.copy()

    # Convert UTC timestamps to Norwegian local time
    weather["timestamp"] = (
        weather["timestamp"].dt.tz_convert("Europe/Oslo")
    )

    # Aggregate geographical points for each timestamp
    hourly = (
        weather.groupby("timestamp")
        .agg({
            "temperature_2m": "mean",
            "precipitation": "mean"
        })
        .reset_index()
    )

    # Extract ISO year and week
    iso_calendar = hourly["timestamp"].dt.isocalendar()

    hourly["iso_year"] = iso_calendar.year
    hourly["iso_week"] = iso_calendar.week

    # Weekly aggregation
    weekly = (
        hourly.groupby(["iso_year", "iso_week"])
        .agg({
            "temperature_2m": "mean",
            "precipitation": "sum"
        })
        .reset_index()
    )

    return weekly


def aggregate_reservoir_weekly(reservoirs):
    reservoirs = reservoirs.copy()

    # Keep one average value per ISO week
    weekly = (
        reservoirs.groupby(["iso_year", "iso_week"])
        .agg({
            "filling_degree": "mean",
            "filling_TWh": "mean",
            "capacity_TWh": "mean",
            "change_in_filling_degree": "mean"
        })
        .reset_index()
    )

    return weekly

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
# WEEKLY AGGREGATION
# --------------------------------------------------

weather_weekly = aggregate_weather_weekly(weather_df)

reservoirs_weekly = aggregate_reservoir_weekly(
    reservoirs_zone
)

# --------------------------------------------------
# ALIGN WEATHER AND RESERVOIR DATA
# --------------------------------------------------

merged_df = pd.merge(
    weather_weekly,
    reservoirs_weekly,
    on=["iso_year", "iso_week"],
    how="inner"
)

# --------------------------------------------------
# DISPLAY RESULTS
# --------------------------------------------------

st.subheader(f"Weekly weather data — {zone}")

st.write(
    f"Number of weeks: {len(weather_weekly)}"
)

st.dataframe(weather_weekly)

st.subheader(f"Weekly reservoir data — {zone}")

st.write(
    f"Number of weeks: {len(reservoirs_weekly)}"
)

st.dataframe(reservoirs_weekly)

st.subheader("Combined dataset")

st.write(
    f"Number of matched weeks: {len(merged_df)}"
)

st.dataframe(merged_df)