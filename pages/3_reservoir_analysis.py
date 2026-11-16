import streamlit as st
import pandas as pd

from app_utils import load_reservoirs, filter_reservoirs
from analysis_utils import (
    plot_stl_decomposition,
    plot_spectrogram,
    apply_plotly_theme
)

st.set_page_config(page_title="Reservoir analysis", layout="wide")

st.title("Reservoir analysis")
st.write("Explore the seasonal and frequency characteristics of reservoir filling levels.")

# Load reservoir data
reservoirs = load_reservoirs()

# Retrieve area selection from Reservoir trends
selected_type = st.session_state.shared_area_type
selected_area = st.session_state.shared_area_number

# Check that the selected area is available
available_areas = sorted(
    reservoirs.loc[
        reservoirs["area_type"] == selected_type,
        "area_number"
    ].dropna().unique()
)

if not available_areas:
    st.warning(f"No areas available for area type {selected_type}.")
    st.stop()

if selected_area not in available_areas:
    selected_area = available_areas[0]
    st.session_state.shared_area_number = selected_area

# Display current selection
st.info(f"Current selection: {selected_type} — Area {selected_area}")

# Filter data
data = filter_reservoirs(
    reservoirs,
    area_type=selected_type
)

data = data[data["area_number"] == selected_area].copy()
data = data.sort_values("date_id")

# Select measurement
measurement = "filling_degree"

# Create tabs
tab1, tab2 = st.tabs(["STL decomposition", "Spectrogram"])

with tab1:
    st.subheader("Seasonal-Trend decomposition")

    seasonal = st.number_input("Seasonal smoother", min_value=7, value=13, step=2)
    trend = st.number_input("Trend smoother", min_value=53, value=53, step=2)
    robust = st.checkbox("Robust decomposition", value=True)

    if st.button("Run STL decomposition"):
        fig = plot_stl_decomposition(
            data,
            seasonal=int(seasonal),
            trend=int(trend),
            robust=robust
        )
        fig = apply_plotly_theme(fig)

        st.plotly_chart(
            fig,
            use_container_width=True
        )

with tab2:
    st.subheader("Spectrogram")

    window_length = st.number_input("Window length (weeks)", min_value=8, value=52)
    window_overlap = st.number_input("Window overlap (weeks)", min_value=0, value=26)

    if window_overlap >= window_length:
        st.warning("Window overlap must be smaller than window length.")
    elif st.button("Generate spectrogram"):
        fig = plot_spectrogram(
            data,
            window_length=int(window_length),
            window_overlap=int(window_overlap)
        )
        fig = apply_plotly_theme(fig)

        st.plotly_chart(
            fig,
            use_container_width=True
        )