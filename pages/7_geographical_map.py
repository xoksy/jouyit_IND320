import json
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from app_utils import load_reservoirs
from weather_utils import load_weather_data

from weather_utils import (
    available_weather_zones,
    load_weather_data,
)

st.set_page_config(page_title="Geographical map", layout="wide")
st.title("Geographical map")
# --------------------------------------------------
# 1. LOAD WEATHER DATA FROM MONGODB
# --------------------------------------------------

st.header("Weather data")

# Retrieve available weather zones
zones = available_weather_zones()

if not zones:
    st.warning("No weather data available in MongoDB.")
    st.stop()

# Load all available weather datasets
weather_dfs = []

with st.spinner("Loading weather data from MongoDB..."):

    for zone in zones:

        zone_df = load_weather_data(zone)

        weather_dfs.append(zone_df)

# Combine all zones into one DataFrame
weather_df = pd.concat(
    weather_dfs,
    ignore_index=True
)

# Ensure timestamp is datetime
weather_df["timestamp"] = pd.to_datetime(
    weather_df["timestamp"],
    utc=True
)

st.success(
    f"{len(zones)} weather zones loaded successfully."
)

# Display dataset information
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
    "Weather zones",
    len(zones)
)

# Display available dates
st.write(
    "Available period:",
    weather_df["timestamp"].min(),
    "to",
    weather_df["timestamp"].max()
)

st.write(
    "Explore Norwegian electricity and reservoir areas. Select a map layer, "
    "a value to display, and a date. Click an area to share the selection "
    "with the other reservoir pages."
)

GEO_DIR = Path(__file__).resolve().parents[1] / "geo"
GEO_FILES = {
    "EL": GEO_DIR / "electricity_areas.geojson",
    "NO": GEO_DIR / "norway_boundary.geojson",
    "VASS": GEO_DIR / "water_reservoir_areas.geojson",
}

@st.cache_data
def read_geojson(path: str):
    with open(path, encoding="utf-8") as file:
        return json.load(file)

@st.cache_data(ttl=3600)
def get_reservoir_data():
    return load_reservoirs()


def get_reservoir_values(area_type, selected_date):
    data = get_reservoir_data().copy()
    data["date_id"] = pd.to_datetime(data["date_id"])
    data = data[data["area_type"] == area_type]
    data["day_diff"] = (data["date_id"].dt.normalize() - pd.Timestamp(selected_date)).abs().dt.days
    if data.empty:
        return {}, None
    nearest = data["day_diff"].min()
    data = data[data["day_diff"] == nearest]
    values = data.groupby("area_number")["filling_degree"].mean().to_dict()
    actual_date = data["date_id"].max().date()
    return values, actual_date


def get_weather_values(selected_date, property_name):
    values = {}
    actual_dates = []
    zones = ["NO1", "NO2", "NO3", "NO4", "NO5"]
    column = "temperature_2m" if property_name == "Temperature" else "precipitation"
    for zone_number, zone in enumerate(zones, start=1):
        try:
            frame = load_weather_data(zone)
            frame["timestamp"] = pd.to_datetime(frame["timestamp"])
            day = frame[frame["timestamp"].dt.date == selected_date]
            if day.empty or column not in day.columns:
                continue
            values[zone_number] = float(day[column].mean())
            actual_dates.append(selected_date)
        except Exception:
            continue
    return values, actual_dates


missing = [str(path) for path in GEO_FILES.values() if not path.exists()]
if missing:
    st.error("GeoJSON files are missing. Run convert_shapefiles.py first.")
    st.code("\n".join(missing))
    st.stop()

col1, col2, col3 = st.columns(3)
with col1:
    area_type = st.selectbox("Magasinstatistikk area type", ["EL", "NO", "VASS"], key="map_area_type")
with col2:
    display_by = st.selectbox("Colour areas by", ["Price area", "Water area", "Weather property"], key="map_display_by")
with col3:
    if display_by == "Weather property":
        weather_property = st.selectbox("Weather property", ["Temperature", "Precipitation"], key="map_weather_property")
    else:
        weather_property = None

try:
    reservoirs = get_reservoir_data()
    available_dates = sorted(pd.to_datetime(reservoirs["date_id"]).dt.date.unique())
except Exception as error:
    st.error(f"Unable to retrieve Magasinstatistikk dates: {error}")
    st.stop()

if not available_dates:
    st.warning("No reservoir dates are available.")
    st.stop()
selected_date = st.select_slider(
    "Select date",
    options=available_dates,
    value=available_dates[-1],
    format_func=lambda value: value.strftime("%d %B %Y"),
    key="map_selected_date",
)

geojson = read_geojson(str(GEO_FILES[area_type]))
features = geojson["features"]

values = {}
value_label = ""
legend_text = ""

if display_by == "Price area":
    if area_type == "EL":
        values = {i: f"NO{i}" for i in range(1, 6)}
        value_label = "Electricity price area"
        legend_text = "Areas are identified by their bidding-zone code. Numeric electricity spot prices are not connected to this app yet."
    else:
        st.info("Price-area colouring is only meaningful for the five EL electricity bidding zones. The map will show the selected geographical outline without price values.")
elif display_by == "Water area":
    values, actual_date = get_reservoir_values(area_type, selected_date)
    value_label = "Reservoir filling"
    if actual_date:
        st.caption(f"Reservoir values: nearest available Magasinstatistikk observation ({actual_date}).")
elif display_by == "Weather property":
    if area_type == "VASS":
        st.warning("Weather data is currently stored by electricity zone (NO1–NO5). A spatial aggregation onto VASS regions requires the underlying weather-point coordinates and a spatial join; this is not inferred from the region-name mapping.")
    else:
        weather_values, _ = get_weather_values(selected_date, weather_property)
        if area_type == "EL":
            values = weather_values
        elif weather_values:
            values = {1: sum(weather_values.values()) / len(weather_values)}
        value_label = "Temperature (°C)" if weather_property == "Temperature" else "Precipitation (mm)"

# Prepare feature properties for the map and legend.
for feature in features:
    props = feature.setdefault("properties", {})
    area_number = int(props.get("area_number", 1))
    value = values.get(area_number)
    props["display_value"] = (
        f"{value:.2f}" if isinstance(value, (int, float)) else str(value or "No data")
    )

# Select colour scale and transparent fill.
def style_function(feature):
    props = feature["properties"]
    number = int(props.get("area_number", 1))
    value = values.get(number)
    if display_by == "Price area" and area_type == "EL":
        palette = {1: "#22D3EE", 2: "#F59E0B", 3: "#A78BFA", 4: "#4ADE80", 5: "#F87171"}
        fill = palette.get(number, "#64748B")
        opacity = 0.28
    elif isinstance(value, (int, float)):
        numeric_values = [v for v in values.values() if isinstance(v, (int, float))]
        low, high = (min(numeric_values), max(numeric_values)) if numeric_values else (0, 1)
        ratio = 0.5 if high == low else (value - low) / (high - low)
        # Sequential blue-to-orange ramp.
        fill = "#2DD4BF" if ratio < 0.33 else ("#60A5FA" if ratio < 0.66 else "#F59E0B")
        opacity = 0.35
    else:
        fill, opacity = "#64748B", 0.12
    selected = (
        st.session_state.get("shared_area_type") == area_type
        and st.session_state.get("shared_area_number") == number
    )
    return {
        "color": "#F8FAFC" if selected else "#94A3B8",
        "weight": 4 if selected else 1.5,
        "fillColor": fill,
        "fillOpacity": opacity,
    }


def highlight_function(_feature):
    return {"weight": 5, "color": "#FDE047", "fillOpacity": 0.5}

# Centre map on Norway.
map_object = folium.Map(location=[64.5, 14.5], zoom_start=4, tiles="CartoDB dark_matter")
folium.GeoJson(
    geojson,
    name=f"{area_type} areas",
    style_function=style_function,
    highlight_function=highlight_function,
    tooltip=folium.GeoJsonTooltip(
        fields=["area_name", "display_value"],
        aliases=["Area:", f"{value_label or 'Value'}:"],
        localize=True,
        sticky=True,
    ),
).add_to(map_object)
folium.LayerControl(collapsed=True).add_to(map_object)

st_folium_result = st_folium(
    map_object,
    width=None,
    height=650,
    key="norway_interactive_map",
    returned_objects=["last_active_drawing"],
)

clicked = st_folium_result.get("last_active_drawing") if st_folium_result else None
if clicked:
    props = clicked.get("properties", {})
    try:
        clicked_type = props.get("area_type", area_type)
        clicked_number = int(props.get("area_number", 1))
        st.session_state.shared_area_type = clicked_type
        st.session_state.shared_area_number = clicked_number
        st.success(f"Selected: {clicked_type} — Area {clicked_number}. This selection is shared with Reservoir trends and Reservoir analysis.")
    except (TypeError, ValueError):
        st.info("Area clicked, but its identifier could not be read.")

if legend_text:
    st.caption(legend_text)
if display_by == "Water area" and not values:
    st.warning("No reservoir filling values were found for the selected date and area type.")
