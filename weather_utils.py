import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import os
from io import BytesIO
from urllib.parse import quote_plus

from dotenv import load_dotenv
from pymongo import MongoClient
from gridfs import GridFSBucket

from scipy.fft import dct, idct
from sklearn.neighbors import LocalOutlierFactor

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
    latest_file = max(files, key=lambda file: file.upload_date)

    # Download file into memory
    with bucket.open_download_stream(latest_file._id) as stream:
        file_data = stream.read()

    # Read Parquet directly from memory
    weather_df = pd.read_parquet(BytesIO(file_data))

    return weather_df

#Add the two functions use in the notebook
def detect_temperature_outliers(
    weather_df,
    region_id,
    outlier_fraction=0.01,
    n_neighbors=20,
):
    # 1. Calculate average temperature for each timestamp
    temperature_mean = (
        weather_df.groupby("timestamp")["temperature_2m"]
        .mean()
        .reset_index()
        .sort_values("timestamp")
    )

    # 2. Remove missing temperature values for LOF
    valid_data = temperature_mean.dropna(
        subset=["temperature_2m"]
    ).copy()

    # Check input parameters
    if not 0 < outlier_fraction <= 0.5:
        raise ValueError("outlier_fraction must be between 0 and 0.5.")

    if len(valid_data) <= n_neighbors:
        raise ValueError("Not enough observations for the selected n_neighbors.")

    # 3. Prepare data for LOF
    X = valid_data[["temperature_2m"]]

    # 4. Initialize and apply LOF
    lof = LocalOutlierFactor(
        contamination=outlier_fraction,
        n_neighbors=n_neighbors
    )

    lof_labels = lof.fit_predict(X)

    # 5. Identify outliers
    valid_data["is_outlier"] = lof_labels == -1

    outliers_df = valid_data[
        valid_data["is_outlier"]
    ].copy()

    # 6. Create the final plot
    figure, axis = plt.subplots(figsize=(16, 6))

    axis.plot(
        temperature_mean["timestamp"],
        temperature_mean["temperature_2m"],
        color="steelblue",
        linewidth=0.7,
        label="Average temperature"
    )

    axis.scatter(
        outliers_df["timestamp"],
        outliers_df["temperature_2m"],
        color="red",
        s=15,
        label="LOF outliers",
        zorder=3
    )

    axis.set_title(
        f"Average hourly temperature and detected outliers — {region_id}"
    )
    axis.set_xlabel("Date")
    axis.set_ylabel("Temperature (°C)")
    axis.grid(alpha=0.3)
    axis.legend()

    figure.tight_layout()

    # 7. Create statistical summary
    summary = {
        "region": region_id,
        "outlier_fraction": outlier_fraction,
        "n_neighbors": n_neighbors,
        "number_of_observations": len(valid_data),
        "number_of_outliers": len(outliers_df),
        "percentage_of_outliers": (
            len(outliers_df) / len(valid_data) * 100
        ),
        "mean_outlier_temperature": (
            outliers_df["temperature_2m"].mean()
        ),
        "min_outlier_temperature": (
            outliers_df["temperature_2m"].min()
        ),
        "max_outlier_temperature": (
            outliers_df["temperature_2m"].max()
        ),
    }

    return figure, outliers_df, summary


def detect_precipitation_outliers(
    weather_df,
    region_id,
    cutoff=100,
    n_std=3,
):
    # 1. Calculate average precipitation for each timestamp
    precipitation_mean = (
        weather_df.groupby("timestamp")["precipitation"]
        .mean()
        .reset_index()
        .sort_values("timestamp")
    )

    # 2. Extract precipitation values
    precipitation = precipitation_mean["precipitation"].to_numpy()

    # Check that the series is valid
    if len(precipitation) == 0 or not np.isfinite(precipitation).all():
        raise ValueError("Precipitation data is empty or contains missing values.")

    if not 0 <= cutoff < len(precipitation):
        raise ValueError("cutoff must be between 0 and the number of observations.")

    if n_std <= 0:
        raise ValueError("n_std must be positive.")

    # 3. Apply DCT high-pass filtering
    precipitation_dct = dct(
        precipitation,
        type=2,
        norm="ortho"
    )

    precipitation_dct[:cutoff] = 0

    satv = idct(
        precipitation_dct,
        type=2,
        norm="ortho"
    )

    # 4. Calculate robust statistics
    satv_median = np.median(satv)
    satv_mad = np.median(np.abs(satv - satv_median))

    robust_std = 1.4826 * satv_mad

    # 5. Calculate SPC boundaries
    lower_limit = satv_median - n_std * robust_std
    upper_limit = satv_median + n_std * robust_std

    # 6. Identify outliers using SATV
    outlier_mask = (
        (satv < lower_limit) |
        (satv > upper_limit)
    )

    precipitation_mean["is_outlier"] = outlier_mask

    # 7. Extract outlier observations
    outliers_df = precipitation_mean[
        precipitation_mean["is_outlier"]
    ].copy()

    # 8. Create final plot
    figure, axis = plt.subplots(figsize=(16, 6))

    axis.plot(
        precipitation_mean["timestamp"],
        precipitation_mean["precipitation"],
        color="steelblue",
        linewidth=0.7,
        label="Average precipitation"
    )

    axis.scatter(
        outliers_df["timestamp"],
        outliers_df["precipitation"],
        color="red",
        s=12,
        label="Outliers",
        zorder=3
    )

    axis.axhline(
        upper_limit,
        color="red",
        linestyle="--",
        label="Upper control limit (UCL)"
    )

    axis.axhline(
        lower_limit,
        color="red",
        linestyle="--",
        label="Lower control limit (LCL)"
    )

    axis.set_title(
        f"Average hourly precipitation and detected outliers — "
        f"{region_id} (2024) - cutoff={cutoff}, n_std={n_std}"
    )

    axis.set_xlabel("Date")
    axis.set_ylabel("Precipitation (mm)")
    axis.grid(alpha=0.3)
    axis.legend()

    figure.tight_layout()

    # 9. Create statistical summary
    summary = {
        "region": region_id,
        "cutoff": cutoff,
        "n_std": n_std,
        "median": satv_median,
        "MAD": satv_mad,
        "lower_limit": lower_limit,
        "upper_limit": upper_limit,
        "number_of_outliers": len(outliers_df),
        "percentage_of_outliers": outlier_mask.mean() * 100,
    }

    return figure, outliers_df, summary