import plotly.graph_objects as go
from analysis_utils import apply_plotly_theme, PLOTLY_COLORS
import requests
import streamlit as st

from app_utils import (
    available_area_types,
    load_reservoirs,
    load_reservoirs_for_period,
    monthly_data,
    numeric_columns,
)


st.set_page_config(page_title="Reservoir trends", layout="wide")

st.title("Reservoir trends")
st.write(
    "Compare a selected reservoir measurement across area numbers over time."
)

try:
    reservoirs = load_reservoirs()
except (requests.RequestException, ValueError) as error:
    st.error(f"Unable to load reservoir data from the NVE API: {error}")
    st.stop()

# --------------------------------------------------
# AREA SELECTION
# --------------------------------------------------
area_types = available_area_types(reservoirs)

selected_type = st.radio(
    "Area type",
    options=area_types,
    index=area_types.index(st.session_state.shared_area_type)
    if st.session_state.shared_area_type in area_types else 0,
    horizontal=True,
    key="trends_area_type"
)

# Update shared area type
st.session_state.shared_area_type = selected_type

# Available areas
available_areas = sorted(
    reservoirs.loc[
        reservoirs["area_type"] == selected_type,
        "area_number"
    ].dropna().unique()
)

# Keep selected area valid
if st.session_state.shared_area_number not in available_areas:
    st.session_state.shared_area_number = available_areas[0]

selected_area = st.selectbox(
    "Area number",
    options=available_areas,
    index=available_areas.index(st.session_state.shared_area_number),
    key="trends_area_number"
)
# Update shared area number
st.session_state.shared_area_number = selected_area


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

area_data = load_reservoirs_for_period(
    start_date=start_date,
    end_date=end_date,
    area_type=selected_type,
)

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
    title=f"{selected_column.replace('_', ' ').capitalize()} – {selected_type} {selected_area}"
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
