import pandas as pd
import streamlit as st

from weather_utils import load_weather_weekly
from app_utils import load_reservoirs
import plotly.express as px

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
    # Load already aggregated weekly weather data
    weather_weekly = load_weather_weekly(
        region_id=zone,
        year=2024
    )

    # Load reservoir data
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

# --------------------------------------------------
# CORRELATION ANALYSIS
# --------------------------------------------------

st.divider()

st.header("Correlation analysis")

col1, col2 = st.columns(2)

with col1:
    weather_variable = st.selectbox(
        "Weather variable",
        ["temperature_2m", "precipitation"],
        format_func=lambda x: {
            "temperature_2m": "Temperature (°C)",
            "precipitation": "Precipitation (mm)"
        }[x]
    )

with col2:
    reservoir_variable = st.selectbox(
        "Reservoir indicator",
        [
            "filling_degree",
            "filling_TWh",
            "change_in_filling_degree"
        ],
        format_func=lambda x: {
            "filling_degree": "Filling degree",
            "filling_TWh": "Filling volume (TWh)",
            "change_in_filling_degree": "Weekly change in filling degree"
        }[x]
    )


# Remove missing values
correlation_data = merged_df[
    [weather_variable, reservoir_variable]
].dropna()


# Calculate Pearson correlation
correlation = correlation_data[
    weather_variable
].corr(
    correlation_data[reservoir_variable],
    method="pearson"
)


# --------------------------------------------------
# DISPLAY CORRELATION
# --------------------------------------------------

st.subheader("Pearson correlation coefficient")

st.metric(
    label="Correlation",
    value=f"{correlation:.3f}"
)

if correlation > 0.7:
    st.success("Strong positive correlation.")

elif correlation > 0.3:
    st.info("Moderate positive correlation.")

elif correlation < -0.7:
    st.success("Strong negative correlation.")

elif correlation < -0.3:
    st.info("Moderate negative correlation.")

else:
    st.warning("Weak or no linear correlation.")


# --------------------------------------------------
# SCATTER PLOT
# --------------------------------------------------

figure = px.scatter(
    correlation_data,
    x=weather_variable,
    y=reservoir_variable,
    title="Weather vs Reservoir relationship",
    labels={
        "temperature_2m": "Temperature (°C)",
        "precipitation": "Precipitation (mm)",
        "filling_degree": "Filling degree",
        "filling_TWh": "Filling volume (TWh)",
        "change_in_filling_degree": "Weekly change in filling degree"
    },
    trendline=None
)

figure.update_layout(
    template="plotly_dark",
    height=550
)

st.plotly_chart(
    figure,
    use_container_width=True
)