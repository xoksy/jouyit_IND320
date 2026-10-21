import streamlit as st

st.set_page_config(page_title="Project information")

st.title("Project information")
st.write(
    "This app explores Norwegian reservoir statistics and physical electricity "
    "flows between European bidding zones."
)

st.header("Data sources")
st.write(
    "Reservoir observations are retrieved from the Norwegian Water Resources "
    "and Energy Directorate (NVE) Magasinstatistikk API. The flow page reads "
    "cross-border measurements from the project's MongoDB collection."
)

st.header("How to explore the app")
st.write(
    "Use the reservoir pages to select an area type (EL, NO, or VASS), inspect "
    "monthly measurement summaries by area number, and choose a date interval "
    "for the trend charts. The cross-border flow page compares the energy "
    "shares of both directions for a selected connection and year, then plots "
    "the physical flows for selected months."
)
