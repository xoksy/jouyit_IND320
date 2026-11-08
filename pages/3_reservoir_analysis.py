import streamlit as st
import pandas as pd

from app_utils import load_reservoirs, filter_reservoirs
from analysis_utils import plot_stl_decomposition, plot_spectrogram

st.set_page_config(page_title="Reservoir analysis", layout="wide")

st.title("Reservoir analysis")
st.write("Explore the seasonal and frequency characteristics of reservoir filling levels.")

# Load reservoir data
reservoirs = load_reservoirs()

# Select area type
area_types = sorted(reservoirs["area_type"].dropna().unique())
selected_type = st.selectbox("Area type", area_types)

# Select area number
available_areas = sorted(
    reservoirs.loc[reservoirs["area_type"] == selected_type, "area_number"].dropna().unique()
)
selected_area = st.selectbox("Area number", available_areas)

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
        st.pyplot(fig)

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
        st.pyplot(fig)