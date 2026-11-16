import plotly.graph_objects as go
from analysis_utils import apply_plotly_theme, PLOTLY_COLORS
import requests
import streamlit as st

from app_utils import (
    load_reservoirs,
    monthly_data,
    numeric_columns,
)


st.set_page_config(page_title="Reservoir trends", layout="wide")

st.title("Reservoir trends")
st.write(
    "Explore the evolution of a selected reservoir measurement "
    "over time for the selected area."
)

try:
    reservoirs = load_reservoirs()
except (requests.RequestException, ValueError) as error:
    st.error(f"Unable to load reservoir data from the NVE API: {error}")
    st.stop()

# --------------------------------------------------
# AREA SELECTION
# --------------------------------------------------
# Retrieve the area selected on the geographical map
selected_type = st.session_state.get("shared_area_type")
selected_area = st.session_state.get("shared_area_number")

# Check that an area has been selected
if selected_type is None or selected_area is None:
    st.warning(
        "No area selected. Please go to Geographical map "
        "and click on an area first."
    )
    st.stop()

# Display the current selection
st.info(f"Current selection: {selected_type} – Area {selected_area}")

# Filter data for the selected area
area_data = reservoirs[
    (reservoirs["area_type"] == selected_type)
    & (reservoirs["area_number"] == selected_area)
].copy()

minimum_date = reservoirs["date_id"].min().date()
maximum_date = reservoirs["date_id"].max().date()
start_date, end_date = st.slider(
    "Select observation interval",
    min_value=minimum_date,
    max_value=maximum_date,
    value=(minimum_date, maximum_date),
    format="YYYY-MM-DD",
)
st.caption(
    "The public API returns its complete dataset; this interval filters which "
    "records are included in the charts."
)

area_data = area_data[
    (area_data["date_id"].dt.date >= start_date)
    & (area_data["date_id"].dt.date <= end_date)
].copy()

area_data = area_data[
    area_data["area_number"] == selected_area
].copy()

columns = numeric_columns(area_data)
if not columns:
    st.info(f"No numeric measurements are available for area type {selected_type}.")
    st.stop()

selected_column = st.selectbox(
    "Measurement",
    options=columns,
    format_func=lambda column: column.replace("_", " ").capitalize(),
)
monthly = monthly_data(area_data, selected_column)
if monthly.empty:
    st.info("No monthly measurements are available for this interval.")
    st.stop()

# --------------------------------------------------
# CREATE INTERACTIVE PLOTLY CHART
# --------------------------------------------------

fig = go.Figure()

for area_number in monthly.columns:

    series = monthly[area_number].dropna()

    if not series.empty:

        fig.add_trace(
            go.Scatter(
                x=series.index,
                y=series,
                mode="lines",
                name=f"Area {area_number}",
                line=dict(width=2),
                hovertemplate=(
                    "Date: %{x|%b %Y}<br>"
                    "Value: %{y:.3f}"
                    "<extra></extra>"
                )
            )
        )

# Apply common theme
fig = apply_plotly_theme(
    fig,
    title=(
        f"{selected_column.replace('_', ' ').capitalize()} "
        f"– {selected_type} Area {selected_area}"
    )
)

fig.update_layout(
    xaxis_title="Month",
    yaxis_title=selected_column.replace("_", " ").capitalize(),
    showlegend=False,
    height=600
)

# Display chart
st.plotly_chart(
    fig,
    use_container_width=True
)
