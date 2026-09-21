import streamlit as st


st.set_page_config(
    page_title="Reservoir data explorer",
    layout="wide",
)

st.title("Reservoir data explorer")
st.write("Explore the reservoir observations imported from the local CSV file.")

st.sidebar.title("Navigation")
st.sidebar.page_link("app.py", label="Home")
st.sidebar.page_link("pages/1_data.py", label="Imported data")
st.sidebar.page_link("pages/2_plot.py", label="Plot")
st.sidebar.page_link("pages/3_info.py", label="Project information")

st.header("Project part 1")
st.write(
    "Use the navigation menu to inspect the imported data, explore time series, "
    "or read the project information page."
)
