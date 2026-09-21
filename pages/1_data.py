import pandas as pd
import streamlit as st

from app_utils import load_reservoirs, monthly_data, numeric_columns


st.set_page_config(page_title="Imported data", layout="wide")

st.title("Imported data")
st.write("One row is shown for each numeric column in the imported CSV data.")

reservoirs = load_reservoirs()
monthly = monthly_data(reservoirs)
columns = numeric_columns(reservoirs)

table = pd.DataFrame(
    {
        "Column": columns,
        "First month": [monthly[column].dropna().iloc[0] for column in columns],
        "Monthly series": [monthly[column].dropna().tolist() for column in columns],
    }
)

st.dataframe(
    table,
    column_config={
        "First month": st.column_config.NumberColumn(format="%.3f"),
        "Monthly series": st.column_config.LineChartColumn(
            "Monthly series",
            y_min=0,
            help="Monthly mean values, starting at the first available month.",
        ),
    },
    hide_index=True,
    use_container_width=True,
)
