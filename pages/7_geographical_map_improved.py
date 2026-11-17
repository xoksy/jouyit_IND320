import json
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from app_utils import load_reservoirs
from weather_utils import load_weather_value_for_date



st.write(
    "Explore Norwegian electricity and reservoir areas. "
    "Select a map layer and a historical period. "
    "The map displays values for the end date of the selected period. "
    "Click an area to share the selection with the other pages."
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
    if area_type == "NO":
        values = {
            1: data["filling_degree"].mean()
        }
    else:
        values = (
            data.groupby("area_number")["filling_degree"]
            .mean()
            .to_dict()
        )
    actual_date = data["date_id"].max().date()
    return values, actual_date


def get_weather_values(selected_date, property_name):

    values = {}

    zones = ["NO1", "NO2", "NO3", "NO4", "NO5"]

    column = (
        "temperature_2m"
        if property_name == "Temperature"
        else "precipitation"
    )

    for zone in zones:

        zone_number = int(zone[-1])

        try:

            value = load_weather_value_for_date(
                region_id=zone,
                selected_date=selected_date,
                column=column
            )

            if value is not None:
                values[zone_number] = value

        except FileNotFoundError:
            continue

    return values


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

    # Keep the complete reservoir date range for forecasting
    reservoir_dates = sorted(
        pd.to_datetime(reservoirs["date_id"]).dt.date.unique()
    )

    # Available dates for the map display
    available_dates = reservoir_dates.copy()

    if display_by == "Weather property":
        weather_start = pd.Timestamp("2024-01-01").date()
        weather_end = pd.Timestamp("2024-12-31").date()

        available_dates = [
            date for date in available_dates
            if weather_start <= date <= weather_end
        ]

except Exception as error:
    st.error(f"Unable to retrieve available dates: {error}")
    st.stop()


if not available_dates:
    st.warning("No dates are available for this selection.")
    st.stop()


# Historical period selection
st.subheader("Historical observation period")

start_date, end_date = st.slider(
    "Select period",
    min_value=reservoir_dates[0],
    max_value=available_dates[-1],
    value=(reservoir_dates[0], available_dates[-1]),
    format="YYYY-MM-DD",
    key="map_observation_interval",
)

# The map displays values for the end date
selected_date = end_date

# Share dates with other pages
st.session_state["map_start_date"] = start_date
st.session_state["map_end_date"] = end_date
st.session_state["map_selected_date"] = selected_date

st.caption(
    "The map displays reservoir values for the end date. "
    "The full selected period is shared with the forecasting page "
    "as the historical training timeframe."
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
        legend_text = "Areas are identified by their bidding-zone code."
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
        weather_values = get_weather_values(
            selected_date,
            weather_property
        )
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

# Assign clearly distinguishable colours to areas.
# Numeric areas are ranked from highest to lowest and receive distinct colours.

RANK_COLORS = [
    "#E63946", "#457B9D", "#F4A261", "#2A9D8F", "#8E5EA2",
    "#E9C46A", "#6D597A", "#43AA8B", "#F15BB5", "#577590",
]


def style_function(feature):
    props = feature["properties"]
    number = int(props.get("area_number", 1))
    value = values.get(number)

    if display_by == "Price area" and area_type == "EL":
        palette = {
            1: "#E63946",
            2: "#457B9D",
            3: "#F4A261",
            4: "#2A9D8F",
            5: "#8E5EA2",
        }
        fill = palette.get(number, "#94A3B8")
        opacity = 0.55

    elif isinstance(value, (int, float)) and pd.notna(value):
        ranked_areas = sorted(
            [
                (area_number, area_value)
                for area_number, area_value in values.items()
                if isinstance(area_value, (int, float))
                and pd.notna(area_value)
            ],
            key=lambda item: item[1],
            reverse=True,
        )
        ranked_numbers = [area_number for area_number, _ in ranked_areas]
        rank = ranked_numbers.index(number)

        if rank < len(RANK_COLORS):
            fill = RANK_COLORS[rank]
        else:
            import colorsys
            hue = (rank * 0.61803398875) % 1
            red, green, blue = colorsys.hsv_to_rgb(hue, 0.62, 0.88)
            fill = "#{:02X}{:02X}{:02X}".format(
                round(red * 255), round(green * 255), round(blue * 255)
            )
        opacity = 0.62

    else:
        fill, opacity = "#94A3B8", 0.20

    selected = (
        st.session_state.get("shared_area_type") == area_type
        and st.session_state.get("shared_area_number") == number
    )
    return {
        "color": "#FFFFFF" if selected else "#526477",
        "weight": 4 if selected else 1.5,
        "fillColor": fill,
        "fillOpacity": opacity,
    }


def highlight_function(_feature):
    return {"weight": 5, "color": "#FDE047", "fillOpacity": 0.5}

# Centre map on Norway.
map_object = folium.Map(
    location=[64.5, 14.5],
    zoom_start=4,
    tiles="OpenStreetMap",
    control_scale=True,
    prefer_canvas=True,
)
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
        display_area = 0 if clicked_type == "NO" else clicked_number
        st.success(
            f"Selected: {clicked_type} — Area {display_area}. "
            "This selection is shared with Reservoir trends and Reservoir analysis."
        )
    except (TypeError, ValueError):
        st.info("Area clicked, but its identifier could not be read.")

if legend_text:
    st.caption(legend_text)
if display_by == "Water area" and not values:
    st.warning("No reservoir filling values were found for the selected date and area type.")
