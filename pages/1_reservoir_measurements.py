import pandas as pd
import requests
import streamlit as st

from app_utils import (
    available_area_types,
    filter_reservoirs,
    load_reservoirs,
    monthly_data,
    numeric_columns,
)


st.set_page_config(page_title="Reservoir measurements", layout="wide")

st.title("Reservoir measurements")
st.write(
    "Browse monthly reservoir measurements by area number. "
    "The source is the Norwegian Water Resources and Energy Directorate (NVE)."
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

area_data = filter_reservoirs(reservoirs, area_type=selected_type)
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

table_rows = []
for area_number in monthly.columns:
    values = monthly[area_number].dropna()
    if not values.empty:
        table_rows.append(
            {
                "Area number": area_number,
                "Latest monthly mean": values.iloc[-1],
                "Monthly series": values.tolist(),
            }
        )

table = pd.DataFrame(table_rows)
if table.empty:
    st.info("No monthly measurements are available for this selection.")
    st.stop()

st.caption(
    f"{len(area_data):,} observations across {len(table)} area numbers "
    f"for area type {selected_type}."
)
st.dataframe(
    table,
    column_config={
        "Latest monthly mean": st.column_config.NumberColumn(format="%.3f"),
        "Monthly series": st.column_config.LineChartColumn(
            "Monthly series",
            help="Monthly mean values for the selected measurement and area type.",
        ),
    },
    hide_index=True,
    width="stretch",
)
