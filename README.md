# Norwegian Energy Data Explorer

## Project Overview

Norwegian Energy Data Explorer is an interactive Streamlit application developed to explore and analyse Norwegian energy and environmental data.

The project combines reservoir statistics, meteorological observations and cross-border electricity flows to provide interactive visualisations, statistical analyses and geographical insights.

## Project Structure

```text
jouyit_IND320/
│
├── .streamlit/             # Streamlit configuration
├── NVE atlas/              # NVE geographical data and resources
├── geo/                    # GeoJSON files for geographical visualisations
├── notebooks/              # Jupyter notebooks for the 4 parts
├── pages/                  # Streamlit application pages
│
├── app.py                  # Main application and navigation
├── app_utils.py            # Reservoir data retrieval and processing
├── weather_utils.py        # Weather data retrieval and anomaly detection
├── analysis_utils.py       # Statistical analysis and visualisation functions
├── convert_shapefiles.py   # Conversion of geographical shapefiles
│
├── requirements.txt        # Python dependencies
├── .gitignore              # Files excluded from Git
└── README.md               # Project documentation
```