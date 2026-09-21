from pathlib import Path

import pandas as pd
import streamlit as st


DATA_PATH = Path(__file__).parent / "data" / "reservoirs.csv"


@st.cache_data
def load_reservoirs():
    """Load and prepare the local reservoir dataset."""
    data = pd.read_csv(DATA_PATH)
    data["date_id"] = pd.to_datetime(data["dato_Id"])
    data = data.rename(
        columns={
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
    )
    return data.sort_values("date_id").reset_index(drop=True)


def monthly_data(data):
    """Return monthly means for numeric columns, indexed by month."""
    numeric_columns = data.select_dtypes(include="number").columns.tolist()
    return data.set_index("date_id")[numeric_columns].resample("MS").mean().dropna(how="all")


def numeric_columns(data):
    return data.select_dtypes(include="number").columns.tolist()
