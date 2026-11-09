import streamlit as st
import pandas as pd

from weather_utils import (
    available_weather_zones,
    load_weather_data,
    detect_precipitation_outliers,
    detect_temperature_outliers,
)

st.set_page_config(
    page_title="Weather anomalies",
    layout="wide",
)

st.title("Weather anomalies")
st.write(
    "Explore meteorological data and detect anomalies "
    "in precipitation and temperature across Norwegian electricity zones."
)

# --------------------------------------------------
# 1. Select available electricity zone
# --------------------------------------------------

zones = available_weather_zones()

if not zones:
    st.warning("No weather data available yet.")
    st.stop()

selected_zone = st.selectbox(
    "Select electricity zone",
    zones,
)

# Load selected zone data
with st.spinner(f"Loading weather data for {selected_zone}..."):
    weather_df = load_weather_data(selected_zone)

st.success(
    f"{selected_zone}: {weather_df['point_id'].nunique()} "
    f"geographical points loaded."
)

# Dataset information
with st.expander("Dataset information"):

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Number of records",
        f"{len(weather_df):,}"
    )

    col2.metric(
        "Geographical points",
        weather_df["point_id"].nunique()
    )

    col3.metric(
        "Number of variables",
        len(weather_df.columns)
    )

# --------------------------------------------------
# 2. Create analysis tabs
# --------------------------------------------------

tab1, tab2 = st.tabs([
    "Precipitation — SPC",
    "Temperature — LOF",
])

# ==================================================
# TAB 1: PRECIPITATION SPC
# ==================================================

with tab1:

    st.subheader("Precipitation anomaly detection")

    st.write(
        "High-pass filtering using the Discrete Cosine Transform (DCT), "
        "followed by robust Statistical Process Control (SPC) boundaries."
    )

    col1, col2 = st.columns(2)

    with col1:
        cutoff = st.number_input(
            "DCT cutoff",
            min_value=1,
            max_value=8000,
            value=100,
            step=10,
        )

    with col2:
        n_std = st.number_input(
            "Number of standard deviations",
            min_value=0.5,
            max_value=10.0,
            value=3.0,
            step=0.5,
        )

    if st.button("Run precipitation analysis"):

        try:
            with st.spinner("Detecting precipitation anomalies..."):

                figure, outliers_df, summary = detect_precipitation_outliers(
                    weather_df,
                    region_id=selected_zone,
                    cutoff=int(cutoff),
                    n_std=float(n_std),
                )

            st.plotly_chart(
                figure,
                use_container_width=True
            )

            st.subheader("Statistical summary")

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Number of outliers",
                f"{summary['number_of_outliers']:,}"
            )

            col2.metric(
                "Outlier percentage",
                f"{summary['percentage_of_outliers']:.2f}%"
            )

            col3.metric(
                "Robust MAD",
                f"{summary['MAD']:.4f}"
            )

            st.write("Control limits")

            col1, col2 = st.columns(2)

            col1.metric(
                "Lower control limit",
                f"{summary['lower_limit']:.4f}"
            )

            col2.metric(
                "Upper control limit",
                f"{summary['upper_limit']:.4f}"
            )

            with st.expander("View detected outliers"):
                st.dataframe(outliers_df, use_container_width=True)

        except ValueError as error:
            st.error(str(error))

# ==================================================
# TAB 2: TEMPERATURE LOF
# ==================================================

with tab2:

    st.subheader("Temperature anomaly detection")

    st.write(
        "Local Outlier Factor (LOF) is used to identify "
        "unusual temperature observations."
    )

    col1, col2 = st.columns(2)

    with col1:
        outlier_fraction = st.number_input(
            "Expected proportion of outliers",
            min_value=0.001,
            max_value=0.5,
            value=0.01,
            step=0.01,
            format="%.3f",
        )

    with col2:
        n_neighbors = st.number_input(
            "Number of neighbors",
            min_value=2,
            max_value=200,
            value=20,
            step=1,
        )

    if st.button("Run temperature analysis"):

        try:
            with st.spinner("Detecting temperature anomalies..."):

                figure, outliers_df, summary = detect_temperature_outliers(
                    weather_df,
                    region_id=selected_zone,
                    outlier_fraction=float(outlier_fraction),
                    n_neighbors=int(n_neighbors),
                )

            st.plotly_chart(
                figure,
                use_container_width=True
            )

            st.subheader("Statistical summary")

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Number of observations",
                f"{summary['number_of_observations']:,}"
            )

            col2.metric(
                "Number of outliers",
                f"{summary['number_of_outliers']:,}"
            )

            col3.metric(
                "Outlier percentage",
                f"{summary['percentage_of_outliers']:.2f}%"
            )

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Mean outlier temperature",
                f"{summary['mean_outlier_temperature']:.2f} °C"
            )

            col2.metric(
                "Minimum outlier temperature",
                f"{summary['min_outlier_temperature']:.2f} °C"
            )

            col3.metric(
                "Maximum outlier temperature",
                f"{summary['max_outlier_temperature']:.2f} °C"
            )

            with st.expander("View detected outliers"):
                st.dataframe(outliers_df, use_container_width=True)

        except ValueError as error:
            st.error(str(error))