import os
from datetime import datetime, timezone
from urllib.parse import quote_plus

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from streamlit.errors import StreamlitSecretNotFoundError


load_dotenv()

RESERVOIR_API_URL = (
    "https://biapi.nve.no/magasinstatistikk/"
    "api/Magasinstatistikk/HentOffentligData"
)
AREA_TYPES = ("EL", "NO", "VASS")
AREA_COLUMNS = {"area_number", "iso_year", "iso_week"}
RESERVOIR_COLUMNS = {
    "omrType": "area_type",
    "omrnr": "area_number",
    "iso_aar": "iso_year",
    "iso_uke": "iso_week",
    "fyllingsgrad": "filling_degree",
    "kapasitet_TWh": "capacity_TWh",
    "fylling_TWh": "filling_TWh",
    "neste_Publiseringsdato": "next_publication_date",
    "fyllingsgrad_forrige_uke": "filling_degree_previous_week",
    "endring_fyllingsgrad": "change_in_filling_degree",
}


def _setting(name: str, default: str | None = None) -> str | None:
    """Read a setting from the environment first, then Streamlit secrets."""
    value = os.getenv(name)
    if value:
        return value

    try:
        value = st.secrets.get(name)
    except StreamlitSecretNotFoundError:
        value = None
    return str(value) if value else default


@st.cache_data(ttl=3600)
def load_reservoirs() -> pd.DataFrame:
    """Retrieve and prepare reservoir observations from the NVE API."""
    response = requests.get(RESERVOIR_API_URL, timeout=30)
    response.raise_for_status()
    payload = response.json()

    if not isinstance(payload, list) or not payload:
        raise ValueError("The Magasinstatistikk API returned no reservoir records.")

    data = pd.DataFrame(payload)
    required_columns = {"dato_Id", "omrType", "omrnr"}
    missing_columns = required_columns.difference(data.columns)
    if missing_columns:
        raise ValueError(
            "The Magasinstatistikk API response is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    data["date_id"] = pd.to_datetime(data["dato_Id"], errors="coerce")
    if data["date_id"].isna().any():
        raise ValueError("The Magasinstatistikk API returned invalid observation dates.")

    data = data.rename(columns=RESERVOIR_COLUMNS)
    if "next_publication_date" in data:
        data["next_publication_date"] = pd.to_datetime(
            data["next_publication_date"],
            errors="coerce",
        )

    for column in data.select_dtypes(include="object").columns:
        if column not in {"area_type"}:
            converted = pd.to_numeric(data[column], errors="coerce")
            if converted.notna().any():
                data[column] = converted

    return data.sort_values("date_id").reset_index(drop=True)

def load_reservoirs_for_period(
    start_date,
    end_date,
    area_type: str | None = None,
) -> pd.DataFrame:
    """
    Return reservoir measurements for a selected period and area type.

    The API returns the complete public dataset, so filtering is performed
    locally after retrieving the cached data.
    """
    reservoirs = load_reservoirs()

    return filter_reservoirs(
        reservoirs,
        area_type=area_type,
        start_date=start_date,
        end_date=end_date,
    )

def available_area_types(data: pd.DataFrame) -> list[str]:
    """Return known reservoir area types in a stable, readable order."""
    present = set(data["area_type"].dropna().astype(str))
    ordered = [area_type for area_type in AREA_TYPES if area_type in present]
    return ordered + sorted(present.difference(ordered))


def filter_reservoirs(
    data: pd.DataFrame,
    area_type: str | None = None,
    start_date=None,
    end_date=None,
) -> pd.DataFrame:
    """Filter reservoir records by area type and inclusive observation dates."""
    selected = data
    if area_type is not None:
        selected = selected[selected["area_type"] == area_type]
    if start_date is not None:
        selected = selected[selected["date_id"] >= pd.Timestamp(start_date)]
    if end_date is not None:
        selected = selected[selected["date_id"] <= pd.Timestamp(end_date)]
    return selected.copy()


def numeric_columns(data: pd.DataFrame) -> list[str]:
    """Return reservoir measurements, excluding numeric area identifiers."""
    return [
        column
        for column in data.select_dtypes(include="number").columns
        if column not in AREA_COLUMNS
    ]


def monthly_data(data: pd.DataFrame, column: str) -> pd.DataFrame:
    """Return monthly means for a measurement, with one column per area number."""
    if data.empty:
        return pd.DataFrame()

    return (
        data.set_index("date_id")
        .groupby("area_number")[column]
        .resample("MS")
        .mean()
        .unstack("area_number")
        .sort_index()
    )


def get_mongo_uri() -> str:
    """Read a MongoDB URI or safely construct one from configured credentials."""
    uri = _setting("MONGODB_URI")
    if uri:
        return uri

    password = _setting("MONGODB_PASSWORD")
    if not password:
        raise RuntimeError(
            "MongoDB is not configured. Set MONGODB_URI or MONGODB_PASSWORD "
            "in the environment or Streamlit secrets."
        )

    username = _setting("MONGODB_USERNAME") or "matthieujouyit_db_user"
    cluster_host = _setting(
        "MONGODB_CLUSTER_HOST",
        "cluster0.l9mrgyg.mongodb.net",
    ) or "cluster0.l9mrgyg.mongodb.net"
    return (
        f"mongodb+srv://{quote_plus(username)}:{quote_plus(password)}"
        f"@{cluster_host}/?appName=Cluster0"
    )


@st.cache_resource
def get_mongo_client(uri: str) -> MongoClient:
    """Create and verify a reusable MongoDB client."""
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
    except PyMongoError:
        client.close()
        raise
    return client


@st.cache_data(ttl=300)
def load_flow_metadata(uri: str) -> tuple[list[tuple[str, str]], list[int]]:
    """Return unique undirected connections and available years."""
    collection = get_mongo_client(uri)["energy_database"]["crossborder_flows"]
    directed_connections = collection.aggregate(
        [
            {
                "$match": {
                    "from_zone": {"$type": "string"},
                    "to_zone": {"$type": "string"},
                }
            },
            {
                "$group": {
                    "_id": {
                        "from_zone": "$from_zone",
                        "to_zone": "$to_zone",
                    }
                }
            }
        ]
    )
    connections = {
        tuple(sorted((row["_id"]["from_zone"], row["_id"]["to_zone"])))
        for row in directed_connections
    }

    first_record = collection.find_one(
        {"timestamp": {"$exists": True}},
        projection={"timestamp": 1},
        sort=[("timestamp", 1)],
    )
    last_record = collection.find_one(
        {"timestamp": {"$exists": True}},
        projection={"timestamp": 1},
        sort=[("timestamp", -1)],
    )
    if not first_record or not last_record:
        return sorted(connections), []

    first_year = pd.Timestamp(first_record["timestamp"]).year
    last_year = pd.Timestamp(last_record["timestamp"]).year
    return sorted(connections), list(range(first_year, last_year + 1))


@st.cache_data(ttl=300)
def load_flows_for_year(
    uri: str,
    connection: tuple[str, str],
    year: int,
) -> pd.DataFrame:
    """Load both directions of a connection for one calendar year."""
    collection = get_mongo_client(uri)["energy_database"]["crossborder_flows"]
    start = datetime(year, 1, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    records = list(
        collection.find(
            {
                "timestamp": {"$gte": start, "$lt": end},
                "$or": [
                    {"from_zone": connection[0], "to_zone": connection[1]},
                    {"from_zone": connection[1], "to_zone": connection[0]},
                ],
            },
            projection={
                "_id": 0,
                "timestamp": 1,
                "flow_mw": 1,
                "from_zone": 1,
                "to_zone": 1,
            },
        ).sort("timestamp", 1)
    )
    data = pd.DataFrame(records)
    if not data.empty:
        data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True)
        data["flow_mw"] = pd.to_numeric(data["flow_mw"], errors="coerce")
        data = data.dropna(subset=["timestamp", "flow_mw"])
    return data
