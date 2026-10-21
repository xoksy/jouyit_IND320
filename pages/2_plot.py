import matplotlib.pyplot as plt
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

area_types = available_area_types(reservoirs)
selected_type = st.radio(
    "Area type",
    options=area_types,
    horizontal=True,
)

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

figure, axis = plt.subplots(figsize=(12, 6))
for area_number in monthly.columns:
    series = monthly[area_number].dropna()
    if not series.empty:
        axis.plot(
            series.index,
            series,
            label=f"Area {area_number}",
            linewidth=1.8,
        )

axis.set_title(
    f"{selected_column.replace('_', ' ').capitalize()} by area number ({selected_type})"
)
axis.set_xlabel("Month")
axis.set_ylabel(selected_column.replace("_", " ").capitalize())
axis.grid(alpha=0.3)
axis.legend(title="Area number")
figure.autofmt_xdate()
figure.tight_layout()
st.pyplot(figure)
