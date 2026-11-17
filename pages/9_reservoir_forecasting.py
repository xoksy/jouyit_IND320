import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from app_utils import load_reservoirs


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


# Display prepared dataset
with st.expander("View prepared dataset"):
    st.dataframe(
        weekly_data.rename("filling_degree (%)").to_frame(),
        use_container_width=True
    )