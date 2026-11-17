import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from app_utils import load_reservoirs
from river import time_series
import numpy as np
from weather_utils import load_weather_data

# --------------------------------------------------
# SNARIMAX FORECASTING
# --------------------------------------------------

def forecast_reservoir_filling(
    weekly_data,
    horizon_weeks=13,
    p=1,
    d=1,
    q=1,
    sp=1,
    sd=1,
    sq=0,
    m=52,
    weekly_weather=None,
    weather_variables=None
):

    series = weekly_data.sort_index().dropna()

    use_weather = bool(weather_variables)

    # --------------------------------------------------
    # 1. Model configuration
    # --------------------------------------------------

    if use_weather:
        # Only one year of weather data is available.
        # Use calendar features instead of seasonal differencing.
        model_sp = 0
        model_sd = 0
        model_sq = 0
        model_m = 1

    else:
        model_sp = sp
        model_sd = sd
        model_sq = sq
        model_m = m

    # Minimum history
    if len(series) < 2 * model_m:
        raise ValueError(
            f"Not enough observations. At least "
            f"{2 * model_m} weekly observations are required."
        )

    # Check weekly frequency
    intervals = series.index.to_series().diff().dropna()

    if not (intervals == pd.Timedelta(days=7)).all():
        raise ValueError(
            "The selected region does not have a regular weekly frequency."
        )

    # --------------------------------------------------
    # 2. Prepare exogenous variables
    # --------------------------------------------------

    def build_weather_features(date):

        iso_week = date.isocalendar().week

        features = {
            "week_sin": float(
                np.sin(2 * np.pi * iso_week / 52)
            ),
            "week_cos": float(
                np.cos(2 * np.pi * iso_week / 52)
            )
        }

        if use_weather:

            matching_week = weekly_weather[
                weekly_weather["iso_week"] == iso_week
            ]

            if matching_week.empty:
                raise ValueError(
                    f"No weather data available for ISO week {iso_week}."
                )

            weather_row = matching_week.iloc[0]

            for variable in weather_variables:
                features[variable] = float(weather_row[variable])

        return features

    if use_weather:

        if weekly_weather is None or weekly_weather.empty:
            raise ValueError("Weather data is not available.")

        # Check that all selected variables exist
        missing_variables = [
            variable
            for variable in weather_variables
            if variable not in weekly_weather.columns
        ]

        if missing_variables:
            raise ValueError(
                f"Missing weather variables: {missing_variables}"
            )

        # Build training features
        training_features = [
            build_weather_features(date)
            for date in series.index
        ]

    else:
        training_features = [
            {
                "week_sin": float(
                    np.sin(2 * np.pi * date.isocalendar().week / 52)
                ),
                "week_cos": float(
                    np.cos(2 * np.pi * date.isocalendar().week / 52)
                )
            }
            for date in series.index
        ]

    # --------------------------------------------------
    # 3. Initialize SNARIMAX
    # --------------------------------------------------

    model = time_series.SNARIMAX(
        p=p,
        d=d,
        q=q,
        sp=model_sp,
        sd=model_sd,
        sq=model_sq,
        m=model_m
    )

    # --------------------------------------------------
    # 4. Train the model
    # --------------------------------------------------

    for value, features in zip(series, training_features):
        model.learn_one(
            float(value),
            x=features
        )

    # --------------------------------------------------
    # 5. Prepare future exogenous variables
    # --------------------------------------------------

    future_dates = pd.date_range(
        start=series.index[-1] + pd.Timedelta(days=7),
        periods=horizon_weeks,
        freq="7D"
    )

    future_features = [
        build_weather_features(date)
        for date in future_dates
    ]

    # --------------------------------------------------
    # 6. Generate forecast
    # --------------------------------------------------

    predictions = list(
        model.forecast(
            horizon=horizon_weeks,
            xs=future_features
        )
    )

    if len(predictions) != horizon_weeks:
        raise ValueError(
            "The model did not return the expected number of predictions."
        )

    if not np.isfinite(predictions).all():
        raise ValueError("The model produced invalid predictions.")

    predictions = np.clip(predictions, 0, 1)

    # --------------------------------------------------
    # 7. Return forecast
    # --------------------------------------------------

    forecast_df = pd.DataFrame({
        "date_id": future_dates,
        "predicted_filling_degree": predictions
    })

    return forecast_df

# --------------------------------------------------
# PREPARE WEATHER DATA
# --------------------------------------------------

@st.cache_data(ttl=3600)
def prepare_weather_data(region_id):

    weather_df = load_weather_data(region_id).copy()

    weather_df["timestamp"] = pd.to_datetime(
        weather_df["timestamp"],
        utc=True
    )

    # Keep 2024 only
    weather_df = weather_df[
        weather_df["timestamp"].dt.year == 2024
    ].copy()

    if weather_df.empty:
        raise ValueError("No weather data available for 2024.")

    iso_dates = weather_df["timestamp"].dt.isocalendar()

    weather_df["iso_year"] = iso_dates.year
    weather_df["iso_week"] = iso_dates.week

    # Keep ISO year 2024 only
    weather_df = weather_df[
        weather_df["iso_year"] == 2024
    ].copy()

    # Aggregate weather data weekly
    weekly_weather = weather_df.groupby(
        ["iso_year", "iso_week"]
    ).agg(
        temperature_2m=("temperature_2m", "mean"),
        precipitation=("precipitation", "sum")
    ).reset_index()

    return weekly_weather

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.title("Reservoir Forecasting")

st.write(
    "Forecast Norwegian reservoir filling using "
    "the SNARIMAX model."
)


# --------------------------------------------------
# RETRIEVE MAP SELECTION
# --------------------------------------------------

selected_type = st.session_state.get("shared_area_type")
selected_area = st.session_state.get("shared_area_number")

start_date = st.session_state.get("map_start_date")
end_date = st.session_state.get("map_end_date")


if selected_type is None or selected_area is None:
    st.warning(
        "Please select an area on the Geographical map first."
    )
    st.stop()

if start_date is None or end_date is None:
    st.warning(
        "Please select a historical period on the Geographical map."
    )
    st.stop()


# NVE uses area_number = 0 for Norway
data_area_number = (
    0 if selected_type == "NO" else selected_area
)


st.info(
    f"Selected area: {selected_type} – Area {data_area_number}"
)

st.write(
    f"Training period: {start_date} → {end_date}"
)


# --------------------------------------------------
# LOAD RESERVOIR DATA
# --------------------------------------------------

@st.cache_data(ttl=3600)
def get_reservoir_data():
    return load_reservoirs()


try:
    reservoirs = get_reservoir_data()

except Exception as error:
    st.error(f"Unable to load reservoir data: {error}")
    st.stop()


# --------------------------------------------------
# FILTER DATA
# --------------------------------------------------

reservoirs["date_id"] = pd.to_datetime(
    reservoirs["date_id"]
)

data = reservoirs[
    (reservoirs["area_type"] == selected_type)
    & (reservoirs["area_number"] == data_area_number)
].copy()


data = data[
    (data["date_id"].dt.date >= start_date)
    & (data["date_id"].dt.date <= end_date)
].copy()


if data.empty:
    st.warning(
        "No reservoir observations are available "
        "for this area and period."
    )
    st.stop()


# --------------------------------------------------
# PREPARE WEEKLY TIME SERIES
# --------------------------------------------------

data["filling_degree"] = pd.to_numeric(
    data["filling_degree"],
    errors="coerce"
)

weekly_data = (
    data.groupby("date_id")["filling_degree"]
    .mean()
    .dropna()
    .sort_index()
)

# Convert filling degree to percentage
weekly_data = weekly_data * 100


# --------------------------------------------------
# DISPLAY DATA
# --------------------------------------------------

st.subheader("Historical reservoir filling")

col1, col2, col3 = st.columns(3)

col1.metric("Observations", len(weekly_data))

col2.metric(
    "Average filling",
    f"{weekly_data.mean():.2f}%"
)

col3.metric(
    "Latest filling",
    f"{weekly_data.iloc[-1]:.2f}%"
)


# Historical time series
fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=weekly_data.index,
        y=weekly_data.values,
        mode="lines",
        name="Reservoir filling",
        line=dict(width=2)
    )
)

fig.update_layout(
    title="Historical reservoir filling",
    xaxis_title="Date",
    yaxis_title="Filling degree (%)",
    hovermode="x unified"
)

st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# FORECAST CONFIGURATION
# --------------------------------------------------

st.divider()
st.header("Forecast configuration")

# Forecast horizon
st.subheader("Forecast horizon")

horizon_weeks = st.slider(
    "Number of weeks to forecast",
    min_value=1,
    max_value=52,
    value=13,
    help="Number of weeks to predict into the future."
)


# --------------------------------------------------
# SNARIMAX CONFIGURATION
# --------------------------------------------------

st.subheader("SNARIMAX parameters")

with st.expander("Advanced model parameters", expanded=True):

    col1, col2, col3 = st.columns(3)

    with col1:
        p = st.number_input("p", 0, 5, 1)
        d = st.number_input("d", 0, 2, 1)
        q = st.number_input("q", 0, 5, 1)

    with col2:
        sp = st.number_input("sp", 0, 5, 1)
        sd = st.number_input("sd", 0, 2, 1)
        sq = st.number_input("sq", 0, 5, 0)

    with col3:
        m = st.number_input(
            "Seasonal period (m)",
            min_value=1,
            max_value=104,
            value=52
        )

st.info(
    "Default parameters correspond to the optimal "
    "SNARIMAX configuration identified in the Jupyter Notebook."
)

# --------------------------------------------------
# EXOGENOUS WEATHER VARIABLES
# --------------------------------------------------

st.divider()

st.subheader("Exogenous weather variables")

st.caption(
    "Weather data is available for 2024 only. "
    "Select the weather variables to include in the model."
)

use_temperature = st.checkbox(
    "Temperature (°C)",
    value=False
)

use_precipitation = st.checkbox(
    "Precipitation (mm)",
    value=False
)

selected_weather_variables = []

if use_temperature:
    selected_weather_variables.append("temperature_2m")

if use_precipitation:
    selected_weather_variables.append("precipitation")

# --------------------------------------------------
# PREPARE MODEL TRAINING DATA
# --------------------------------------------------

if selected_weather_variables:

    # Weather data is only available for 2024
    training_data = reservoirs[
        (reservoirs["area_type"] == selected_type)
        & (reservoirs["area_number"] == data_area_number)
        & (reservoirs["date_id"] >= "2024-01-01")
        & (reservoirs["date_id"] < "2025-01-01")
    ].copy()

else:

    # Use the period selected on the geographical map
    training_data = data.copy()


if training_data.empty:
    st.warning(
        "No reservoir observations are available "
        "for the selected training period."
    )
    st.stop()


training_data["filling_degree"] = pd.to_numeric(
    training_data["filling_degree"],
    errors="coerce"
)

training_weekly_data = (
    training_data.groupby("date_id")["filling_degree"]
    .mean()
    .dropna()
    .sort_index()
)

# --------------------------------------------------
# LOAD WEATHER DATA
# --------------------------------------------------

weekly_weather = None

if selected_weather_variables:

    if selected_type == "EL":

        weather_region = f"NO{data_area_number}"

    elif selected_type == "NO":

        st.warning(
            "Weather data for Norway must be aggregated "
            "from the five electricity zones."
        )
        weather_region = None

    else:

        st.warning(
            "Weather data is not directly available "
            "for VASS areas."
        )
        weather_region = None

    if weather_region is not None:

        try:
            with st.spinner(f"Loading weather data for {weather_region}..."):
                weekly_weather = prepare_weather_data(weather_region)

            st.success(
                f"Weather data loaded for {weather_region}."
            )

            st.write(
                f"Number of available weeks: {len(weekly_weather)}"
            )

            st.dataframe(
                weekly_weather.head(10),
                use_container_width=True
            )

        except Exception as error:
            st.error(
                f"Unable to load weather data: {error}"
            )

# --------------------------------------------------
# FORECAST SUMMARY
# --------------------------------------------------

st.subheader("Configuration summary")

st.write("**Model:** SNARIMAX (River)")
st.write(f"**Forecast horizon:** {horizon_weeks} weeks")

if selected_weather_variables:
    st.write(f"**Training period:** "f"{training_weekly_data.index.min().date()} → "f"{training_weekly_data.index.max().date()}")
    st.caption("Training period restricted to 2024 because of weather data availability.")
else:
    st.write(f"**Training period:** {start_date} → {end_date}")

st.write(
    f"**Parameters:** "
    f"(p={p}, d={d}, q={q}) "
    f"(sp={sp}, sd={sd}, sq={sq}, m={m})"
)

# --------------------------------------------------
# RUN FORECAST
# --------------------------------------------------

st.divider()
st.subheader("Generate forecast")

if st.button("Run SNARIMAX forecast", type="primary"):
    if selected_weather_variables and weekly_weather is None:
        st.error(
            "Weather data could not be loaded. "
            "Please check the selected area and weather availability."
        )
        st.stop()

    try:
        with st.spinner("Training SNARIMAX model..."):

            forecast_df = forecast_reservoir_filling(
                weekly_data=training_weekly_data,
                horizon_weeks=horizon_weeks,
                p=p,
                d=d,
                q=q,
                sp=sp,
                sd=sd,
                sq=sq,
                m=m,
                weekly_weather=weekly_weather,
                weather_variables=selected_weather_variables
            )

        st.session_state["reservoir_forecast"] = forecast_df
        st.success("Forecast successfully generated!")

    except Exception as error:
        st.error(f"Forecasting error: {error}")

# --------------------------------------------------
# DISPLAY FORECAST
# --------------------------------------------------

if "reservoir_forecast" in st.session_state:

    forecast_df = st.session_state["reservoir_forecast"].copy()

    st.subheader("Reservoir filling forecast")

    # Check whether weather variables are being used
    using_weather = bool(selected_weather_variables)

    # Prepare historical data
    historical_data = weekly_data.copy()
    historical_data.index = pd.to_datetime(historical_data.index)

    if using_weather:
        # Keep only 2024 historical data
        historical_data = historical_data[
            historical_data.index.year == 2024
        ]

        # Display only the first 12 forecast weeks
        forecast_df["date_id"] = pd.to_datetime(forecast_df["date_id"])
        forecast_plot_df = forecast_df[
            forecast_df["date_id"] <=
            forecast_df["date_id"].min() + pd.Timedelta(weeks=12)
        ]

        forecast_color = "orange"
        forecast_name = "SNARIMAX forecast (with weather)"

    else:
        forecast_plot_df = forecast_df
        forecast_color = "#3867d6"
        forecast_name = "SNARIMAX forecast"

    forecast_fig = go.Figure()

    # Historical data
    forecast_fig.add_trace(
        go.Scatter(
            x=historical_data.index,
            y=historical_data.values,
            mode="lines",
            name="Historical filling",
            line=dict(color="#87CEFA", width=2.5)
        )
    )

    # Forecast
    forecast_fig.add_trace(
        go.Scatter(
            x=forecast_plot_df["date_id"],
            y=forecast_plot_df["predicted_filling_degree"] * 100,
            mode="lines+markers",
            name=forecast_name,
            line=dict(
                color=forecast_color,
                dash="dash",
                width=3
            ),
            marker=dict(size=7)
        )
    )

    forecast_fig.update_layout(
        title="Historical data and reservoir filling forecast",
        xaxis_title="Date",
        yaxis_title="Filling degree (%)",
        hovermode="x unified"
    )

    st.plotly_chart(
        forecast_fig,
        use_container_width=True
    )

    # Display forecast table
    display_df = forecast_df.assign(
        predicted_filling_degree=lambda df:
            df["predicted_filling_degree"] * 100
    ).rename(columns={
        "predicted_filling_degree": "Predicted filling (%)"
    })

    st.dataframe(
        display_df,
        use_container_width=True
    )
