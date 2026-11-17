import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from app_utils import load_reservoirs
from river import time_series
import numpy as np

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
    m=52
):

    # 1. Prepare the time series
    series = weekly_data.sort_index().dropna()

    if len(series) < 2 * m:
        raise ValueError(
            f"Not enough observations. At least {2*m} "
            "weekly observations are required."
        )

    # 2. Check weekly frequency
    intervals = series.index.to_series().diff().dropna()

    if not (intervals == pd.Timedelta(days=7)).all():
        raise ValueError(
            "The selected region does not have a regular weekly frequency."
        )

    # 3. Initialize SNARIMAX
    model = time_series.SNARIMAX(
        p=p,
        d=d,
        q=q,
        sp=sp,
        sd=sd,
        sq=sq,
        m=m
    )

    # 4. Train the model
    for value in series:
        model.learn_one(float(value))

    # 5. Generate predictions
    predictions = list(
        model.forecast(horizon= horizon_weeks)
    )

    if len(predictions) != horizon_weeks:
        raise ValueError(
            "The model did not return the expected number of predictions."
        )

    if not np.isfinite(predictions).all():
        raise ValueError("The model produced invalid predictions.")

    predictions = np.clip(predictions, 0, 1)

    # 6. Generate future dates
    future_dates = pd.date_range(
        start=series.index[-1] + pd.Timedelta(days=7),
        periods=horizon_weeks,
        freq="7D"
    )

    # 7. Return forecast
    forecast_df = pd.DataFrame({
        "date_id": future_dates,
        "predicted_filling_degree": predictions
    })

    return forecast_df
# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.title("Reservoir Forecasting")

st.write(
    "Forecast Norwegian reservoir filling using "
    "statistical and machine learning models."
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

# Model selection
model_type = st.selectbox(
    "Forecasting model",
    ["SNARIMAX (River)", "Machine Learning"]
)

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
# SNARIMAX PARAMETERS
# --------------------------------------------------

if model_type == "SNARIMAX (River)":

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


elif model_type == "Machine Learning":

    st.info(
        "Machine Learning forecasting will be implemented "
        "in the next development step."
    )


# --------------------------------------------------
# FORECAST SUMMARY
# --------------------------------------------------

st.subheader("Configuration summary")

st.write(f"**Model:** {model_type}")
st.write(f"**Forecast horizon:** {horizon_weeks} weeks")
st.write(f"**Training period:** {start_date} → {end_date}")

if model_type == "SNARIMAX (River)":

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

if model_type == "SNARIMAX (River)":

    if st.button("Run SNARIMAX forecast", type="primary"):

        try:
            with st.spinner("Training SNARIMAX model..."):

                forecast_df = forecast_reservoir_filling(
                    weekly_data=weekly_data / 100,
                    horizon_weeks=horizon_weeks,
                    p=p,
                    d=d,
                    q=q,
                    sp=sp,
                    sd=sd,
                    sq=sq,
                    m=m
                )

            st.session_state["reservoir_forecast"] = forecast_df

            st.success("Forecast successfully generated!")

        except Exception as error:
            st.error(f"Forecasting error: {error}")

# --------------------------------------------------
# DISPLAY FORECAST
# --------------------------------------------------

if "reservoir_forecast" in st.session_state:

    forecast_df = st.session_state["reservoir_forecast"]

    st.subheader("Reservoir filling forecast")

    forecast_fig = go.Figure()

    # Historical data
    forecast_fig.add_trace(
        go.Scatter(
            x=weekly_data.index,
            y=weekly_data.values,
            mode="lines",
            name="Historical filling"
        )
    )

    # Forecast
    forecast_fig.add_trace(
        go.Scatter(
            x=forecast_df["date_id"],
            y=forecast_df["predicted_filling_degree"] * 100,
            mode="lines+markers",
            name="SNARIMAX forecast",
            line=dict(dash="dash", width=3)
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

    st.dataframe(
        forecast_df.assign(
            predicted_filling_degree=lambda df:
                df["predicted_filling_degree"] * 100
        ).rename(columns={
            "predicted_filling_degree": "Predicted filling (%)"
        }),
        use_container_width=True
    )

# Display prepared dataset
with st.expander("View prepared dataset"):
    st.dataframe(
        weekly_data.rename("filling_degree (%)").to_frame(),
        use_container_width=True
    )