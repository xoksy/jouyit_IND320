import streamlit as st

st.set_page_config(
    page_title="Reservoir data explorer",
    layout="wide",
)

pages = {
    "Navigation": [
        st.Page("pages/0_home.py", title="Home"),
        st.Page("pages/1_data.py", title="Imported data"),
        st.Page("pages/2_plot.py", title="Plot"),
        st.Page("pages/3_info.py", title="Project information"),
    ]
}

pg = st.navigation(pages)

pg.run()