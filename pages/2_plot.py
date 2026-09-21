import matplotlib.pyplot as plt
import streamlit as st

from app_utils import load_reservoirs, monthly_data, numeric_columns


st.set_page_config(page_title="Reservoir plot", layout="wide")

st.title("Reservoir data over time")
st.write("Choose one numeric column or compare all numeric columns on the same chart.")

reservoirs = load_reservoirs()
monthly = monthly_data(reservoirs)
columns = numeric_columns(reservoirs)

selected_column = st.selectbox(
    "Column to plot",
    options=["All numeric columns", *columns],
)

month_options = list(monthly.index)
selected_month = st.select_slider(
    "Show data up to month",
    options=month_options,
    value=month_options[0],
    format_func=lambda month: month.strftime("%Y-%m"),
)

plot_data = monthly.loc[:selected_month]
plot_columns = columns if selected_column == "All numeric columns" else [selected_column]

figure, axis = plt.subplots(figsize=(12, 6))
for column in plot_columns:
    axis.plot(plot_data.index, plot_data[column], label=column, linewidth=1.8)

axis.set_title("Monthly reservoir measurements")
axis.set_xlabel("Month")
axis.set_ylabel("Monthly mean value")
axis.grid(alpha=0.3)
axis.legend(title="Variable")
figure.autofmt_xdate()
figure.tight_layout()
st.pyplot(figure)
