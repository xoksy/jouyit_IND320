"""Convert the supplied NVE shapefiles into web-map GeoJSON files."""
from pathlib import Path
import geopandas as gpd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "geo"
OUT.mkdir(exist_ok=True)

# EL: five Norwegian electricity bidding areas.
el = gpd.read_file(ROOT / "Budområder.shp").to_crs("EPSG:4326")
el["area_type"] = "EL"
el["area_number"] = el["budomr"].str.extract(r"(\d+)").astype(int)
el["area_name"] = el["budomr"].str.replace(" ", "", regex=False)
el[["area_type", "area_number", "area_name", "geometry"]].to_file(
    OUT / "electricity_areas.geojson", driver="GeoJSON"
)

# Precipitation regions: keep the original five regions for weather aggregation.
precip = gpd.read_file(ROOT / "NVE_Region.shp").to_crs("EPSG:4326")
precip["REGION"] = precip["REGION"].replace({"RØ": "RO"})
precip[["REGION", "REGIONNAVN", "geometry"]].to_file(
    OUT / "precipitation_regions.geojson", driver="GeoJSON"
)

# VASS mapping explicitly supplied by the project assignment/user:
# VASS 1 = RS + RØ, VASS 2 = RV, VASS 3 = RM + RN.
vass_mapping = {"RS": 1, "RO": 1, "RV": 2, "RM": 3, "RN": 3}
precip["area_number"] = precip["REGION"].map(vass_mapping)
precip["area_type"] = "VASS"
precip["area_name"] = precip["area_number"].map(
    {1: "VASS Area 1", 2: "VASS Area 2", 3: "VASS Area 3"}
)
vass = precip.dissolve(by=["area_type", "area_number", "area_name"], as_index=False)
vass[["area_type", "area_number", "area_name", "geometry"]].to_file(
    OUT / "water_reservoir_areas.geojson", driver="GeoJSON"
)

# NO is the union of the five NVE precipitation regions, yielding one Norway outline.
norway = precip.dissolve()
norway["area_type"] = "NO"
norway["area_number"] = 1
norway["area_name"] = "Norway"
norway[["area_type", "area_number", "area_name", "geometry"]].to_file(
    OUT / "norway_boundary.geojson", driver="GeoJSON"
)

print("GeoJSON files created in", OUT)
for path in sorted(OUT.glob("*.geojson")):
    frame = gpd.read_file(path)
    print(f"{path.name}: {len(frame)} feature(s), CRS={frame.crs}")
