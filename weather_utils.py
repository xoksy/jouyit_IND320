import streamlit as st
import pandas as pd
import numpy as np

import os
from io import BytesIO
from urllib.parse import quote_plus

from dotenv import load_dotenv
from pymongo import MongoClient
from gridfs import GridFSBucket

from scipy.fft import dct, idct
from sklearn.neighbors import LocalOutlierFactor

import plotly.graph_objects as go
from analysis_utils import PLOTLY_COLORS

# --------------------------------------------------
# MONGODB CONNECTION
# --------------------------------------------------

@st.cache_resource
def get_weather_bucket():

    # Local development: use .env
    load_dotenv()

    password = os.getenv("MONGODB_PASSWORD")

    # Streamlit Cloud: use Secrets
    if "MONGODB_PASSWORD" in st.secrets:
        password = st.secrets["MONGODB_PASSWORD"]

    if not password:
        raise ValueError("MongoDB password not configured.")

    password = quote_plus(password)

    uri = (
        f"mongodb+srv://matthieujouyit_db_user:{password}"
        "@cluster0.l9mrgyg.mongodb.net/?appName=Cluster0"
    )

    client = MongoClient(
        uri,
        serverSelectionTimeoutMS=10000
    )

    client.admin.command("ping")

    mongo_db = client["energy_database"]

    bucket = GridFSBucket(
        mongo_db,
        bucket_name="weather_files"
    )

    return bucket


# --------------------------------------------------
# AVAILABLE WEATHER ZONES
# --------------------------------------------------

@st.cache_data(ttl=60)
def available_weather_zones():

    bucket = get_weather_bucket()

    available = []

    for file in bucket.find():

        region = file.metadata.get("region")

        if region and region not in available:
            available.append(region)

    zones = ["NO1", "NO2", "NO3", "NO4", "NO5"]

    return [zone for zone in zones if zone in available]


# --------------------------------------------------
# LOAD WEATHER DATA FROM MONGODB
# --------------------------------------------------

@st.cache_data
def load_weather_data(region_id):

    bucket = get_weather_bucket()

    filename = f"weather_{region_id}.parquet"

    files = list(bucket.find({
        "filename": filename,
        "metadata.region": region_id
    }))

    if not files:
        raise FileNotFoundError(
            f"Weather data not found for {region_id}."
        )

    # Select the most recent version
    latest_file = max(
        files,
        key=lambda file: file.upload_date
    )

    # Download file into memory
    with bucket.open_download_stream(latest_file._id) as stream:
        file_data = stream.read()

    # Read Parquet directly from memory
    weather_df = pd.read_parquet(BytesIO(file_data))

    return weather_df

# --------------------------------------------------
# LOAD ONLY ONE WEATHER VALUE FOR A SELECTED DATE
# --------------------------------------------------

@st.cache_data(ttl=3600)
def load_weather_value_for_date(region_id, selected_date, column):

    if column not in ["temperature_2m", "precipitation"]:
        raise ValueError("Invalid weather column.")

    bucket = get_weather_bucket()

    filename = f"weather_{region_id}.parquet"

    files = list(bucket.find({
        "filename": filename,
        "metadata.region": region_id
    }))

    if not files:
        raise FileNotFoundError(
            f"Weather data not found for {region_id}."
        )

    latest_file = max(
        files,
        key=lambda file: file.upload_date
    )

    # Download the file
    with bucket.open_download_stream(latest_file._id) as stream:
        file_data = stream.read()

    # Read only the two required columns
    weather_df = pd.read_parquet(
        BytesIO(file_data),
        columns=["timestamp", column]
    )

    # Release the downloaded file bytes
    del file_data

    weather_df["timestamp"] = pd.to_datetime(
        weather_df["timestamp"],
        utc=True
    )

    # Filter the selected date
    daily_data = weather_df[
        weather_df["timestamp"].dt.date == selected_date
    ]

    if daily_data.empty:
        return None

    # Return only one aggregated value
    return float(daily_data[column].mean())


# --------------------------------------------------
# WEATHER ANOMALIES — LOCAL OUTLIER FACTOR
# --------------------------------------------------

def detect_temperature_outliers(
    weather_df,
    region_id,
    weather_property="Temperature",
    outlier_fraction=0.01,
    n_neighbors=20,
):

    # 1. Select the weather variable
    property_config = {
        "Temperature": {
            "column": "temperature_2m",
            "label": "Temperature",
            "unit": "°C",
            "color": PLOTLY_COLORS["temperature"],
        },
        "Precipitation": {
            "column": "precipitation",
            "label": "Precipitation",
            "unit": "mm",
            "color": PLOTLY_COLORS["precipitation"],
        },
    }

    if weather_property not in property_config:
        raise ValueError("Invalid weather property.")

    config = property_config[weather_property]

    column = config["column"]
    label = config["label"]
    unit = config["unit"]

    # 2. Calculate average value for each timestamp
    property_mean = (
        weather_df.groupby("timestamp")[column]
        .mean()
        .reset_index()
        .sort_values("timestamp")
    )

    # 3. Remove missing values
    valid_data = property_mean.dropna(
        subset=[column]
    ).copy()

    # Check input parameters
    if not 0 < outlier_fraction <= 0.5:
        raise ValueError(
            "outlier_fraction must be between 0 and 0.5."
        )

    if len(valid_data) <= n_neighbors:
        raise ValueError(
            "Not enough observations for the selected n_neighbors."
        )

    # 4. Prepare data for LOF
    X = valid_data[[column]]

    # 5. Initialize and apply LOF
    lof = LocalOutlierFactor(
        contamination=outlier_fraction,
        n_neighbors=n_neighbors
    )

    lof_labels = lof.fit_predict(X)

    # 6. Identify outliers
    valid_data["is_outlier"] = lof_labels == -1

    outliers_df = valid_data[
        valid_data["is_outlier"]
    ].copy()

    # 7. Create interactive Plotly figure
    figure = go.Figure()

    # Average weather property
    figure.add_trace(
        go.Scatter(
            x=property_mean["timestamp"],
            y=property_mean[column],
            mode="lines",
            name=f"Average {label.lower()}",
            line=dict(
                color=config["color"],
                width=1.5
            ),
            hovertemplate=(
                "Date: %{x|%d %b %Y %H:%M}<br>"
                f"{label}: %{{y:.2f}} {unit}"
                "<extra></extra>"
            )
        )
    )

    # LOF outliers
    figure.add_trace(
        go.Scatter(
            x=outliers_df["timestamp"],
            y=outliers_df[column],
            mode="markers",
            name="LOF outliers",
            marker=dict(
                color=PLOTLY_COLORS["anomaly"],
                size=7
            ),
            hovertemplate=(
                "Date: %{x|%d %b %Y %H:%M}<br>"
                f"{label}: %{{y:.2f}} {unit}"
                "<extra>LOF outlier</extra>"
            )
        )
    )

    figure.update_layout(
        title=(
            f"Average hourly {label.lower()} "
            f"and detected outliers — {region_id}"
        ),
        xaxis_title="Date",
        yaxis_title=f"{label} ({unit})",
        hovermode="x unified",
        template="plotly_dark",
        height=550,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    # 8. Create statistical summary
    summary = {
        "region": region_id,
        "weather_property": weather_property,
        "outlier_fraction": outlier_fraction,
        "n_neighbors": n_neighbors,
        "number_of_observations": len(valid_data),
        "number_of_outliers": len(outliers_df),
        "percentage_of_outliers": (
            len(outliers_df) / len(valid_data) * 100
        ),
        "mean_outlier_value": outliers_df[column].mean(),
        "min_outlier_value": outliers_df[column].min(),
        "max_outlier_value": outliers_df[column].max(),
    }

    return figure, outliers_df, summary


# --------------------------------------------------
# WEATHER ANOMALIES — DCT + ROBUST SPC (SATV)
# --------------------------------------------------

def detect_precipitation_outliers(
    weather_df,
    region_id,
    weather_property="Temperature",
    cutoff=100,
    n_std=3,
):

    # 1. Select the weather variable
    property_config = {
        "Temperature": {
            "column": "temperature_2m",
            "label": "Temperature",
            "unit": "°C",
            "color": PLOTLY_COLORS["temperature"],
        },
        "Precipitation": {
            "column": "precipitation",
            "label": "Precipitation",
            "unit": "mm",
            "color": PLOTLY_COLORS["precipitation"],
        },
    }

    if weather_property not in property_config:
        raise ValueError("Invalid weather property.")

    config = property_config[weather_property]

    column = config["column"]
    label = config["label"]
    unit = config["unit"]

    # 2. Calculate average value for each timestamp
    property_mean = (
        weather_df.groupby("timestamp")[column]
        .mean()
        .reset_index()
        .sort_values("timestamp")
    )

    # 3. Extract values
    values = property_mean[column].to_numpy()

    # Check that the series is valid
    if len(values) == 0 or not np.isfinite(values).all():
        raise ValueError(
            f"{label} data is empty or contains missing values."
        )

    if not 0 <= cutoff < len(values):
        raise ValueError(
            "cutoff must be between 0 and the number of observations."
        )

    if n_std <= 0:
        raise ValueError("n_std must be positive.")

    # 4. Apply DCT high-pass filtering
    values_dct = dct(
        values,
        type=2,
        norm="ortho"
    )

    values_dct[:cutoff] = 0

    satv = idct(
        values_dct,
        type=2,
        norm="ortho"
    )

    # 5. Calculate robust statistics
    satv_median = np.median(satv)

    satv_mad = np.median(
        np.abs(satv - satv_median)
    )

    robust_std = 1.4826 * satv_mad

    # 6. Calculate SPC boundaries on SATV
    satv_lower_limit = satv_median - n_std * robust_std
    satv_upper_limit = satv_median + n_std * robust_std

    # 7. Identify outliers using SATV
    outlier_mask = (
        (satv < satv_lower_limit) |
        (satv > satv_upper_limit)
    )
    property_mean["is_outlier"] = outlier_mask

    outliers_df = property_mean[
        property_mean["is_outlier"]
    ].copy()

    # 8. Project SPC boundaries onto the original weather scale
    baseline = values - satv

    lower_limit_curve = baseline + satv_lower_limit
    upper_limit_curve = baseline + satv_upper_limit

    # 9. Extract outlier observations
    outliers_df = property_mean[
        property_mean["is_outlier"]
    ].copy()

    # 10. Create interactive Plotly figure
    figure = go.Figure()

    # Average weather property
    figure.add_trace(
        go.Scatter(
            x=property_mean["timestamp"],
            y=property_mean[column],
            mode="lines",
            name=f"Average {label.lower()}",
            line=dict(
                color=config["color"],
                width=1.5
            ),
            hovertemplate=(
                "Date: %{x|%d %b %Y %H:%M}<br>"
                f"{label}: %{{y:.2f}} {unit}"
                "<extra></extra>"
            )
        )
    )

    # SATV outliers
    figure.add_trace(
        go.Scatter(
            x=outliers_df["timestamp"],
            y=outliers_df[column],
            mode="markers",
            name="SATV outliers",
            marker=dict(
                color=PLOTLY_COLORS["anomaly"],
                size=7
            ),
            hovertemplate=(
                "Date: %{x|%d %b %Y %H:%M}<br>"
                f"{label}: %{{y:.2f}} {unit}"
                "<extra>SATV outlier</extra>"
            )
        )
    )

    # Upper control limit
    figure.add_trace(
        go.Scatter(
            x=property_mean["timestamp"],
            y=upper_limit_curve,
            mode="lines",
            name="Upper control limit (UCL)",
            line=dict(
                color=PLOTLY_COLORS["anomaly"],
                width=1.5,
                dash="dash"
            )
        )
    )

    # Lower control limit
    figure.add_trace(
        go.Scatter(
            x=property_mean["timestamp"],
            y=lower_limit_curve,
            mode="lines",
            name="Lower control limit (LCL)",
            line=dict(
                color=PLOTLY_COLORS["anomaly"],
                width=1.5,
                dash="dash"
            )
        )
    )

    figure.update_layout(
        title=(
            f"Average hourly {label.lower()} and detected outliers "
            f"— {region_id} - cutoff={cutoff}, n_std={n_std}"
        ),
        xaxis_title="Date",
        yaxis_title=f"{label} ({unit})",
        hovermode="x unified",
        template="plotly_dark",
        height=550,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    # 10. Create statistical summary
    summary = {
        "region": region_id,
        "weather_property": weather_property,
        "cutoff": cutoff,
        "n_std": n_std,
        "median": satv_median,
        "MAD": satv_mad,
        "lower_limit": float(np.median(lower_limit_curve)),
        "upper_limit": float(np.median(upper_limit_curve)),     
        "number_of_outliers": len(outliers_df),
        "percentage_of_outliers": (
            outlier_mask.mean() * 100
        ),
    }

    return figure, outliers_df, summary