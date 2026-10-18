import streamlit as st

st.set_page_config(
    page_title="Reservoir data explorer",
    layout="wide",
)

pages = {
    "Navigation": [
        st.Page("pages/0_home.py", title="Home"),
        st.Page("pages/1_data.py", title="Reservoir measurements"),
        st.Page("pages/2_plot.py", title="Reservoir trends"),
        st.Page("pages/3_flows.py", title="Cross-border flows"),
        st.Page("pages/4_info.py", title="Project information"),
    ]
}

pg = st.navigation(pages)

pg.run()