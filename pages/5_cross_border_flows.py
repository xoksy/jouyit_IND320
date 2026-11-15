import calendar
import pandas as pd
import plotly.graph_objects as go
from analysis_utils import apply_plotly_theme, PLOTLY_COLORS
import streamlit as st
from pymongo.errors import OperationFailure, PyMongoError

from app_utils import get_mongo_uri, load_flow_metadata, load_flows_for_year


st.set_page_config(page_title="Cross-border flows", layout="wide")

st.title("Cross-border electricity flows")
st.write(
    "Compare the annual energy-flow shares in both directions and inspect "
    "physical power flows for selected months."
)

try:
    mongo_uri = get_mongo_uri()
    connections, years = load_flow_metadata(mongo_uri)
except OperationFailure as error:
    if error.code == 18 or "authentication failed" in str(error).lower():
        st.error(
            "MongoDB Atlas rejected the database credentials. Check that "
            "MONGODB_URI (or MONGODB_PASSWORD) uses the password for a MongoDB "
            "database user, not your Atlas account password."
        )
        st.info(
            "If the password contains special characters, use MONGODB_PASSWORD "
            "so the app can URL-encode it, or percent-encode it in "
            "MONGODB_URI. If both settings are present, MONGODB_URI takes "
            "precedence. Also verify the database username and cluster host."
        )
        st.stop()
    st.error(f"Unable to load cross-border flow data from MongoDB: {error}")
    st.stop()
except (PyMongoError, RuntimeError, ValueError) as error:
    st.error(f"Unable to load cross-border flow data from MongoDB: {error}")
    st.stop()

if not connections or not years:
    st.info("No cross-border connections or years are available in MongoDB.")
    st.stop()

connection_labels = {
    connection: f"{connection[0]} ↔ {connection[1]}"
    for connection in connections
}
left_column, right_column = st.columns(2)

with left_column:
    selected_connection = st.radio(
        "Connection",
        options=connections,
        format_func=lambda connection: connection_labels[connection],
    )
    selected_year = st.selectbox(
        "Year",
        options=years,
        index=len(years) - 1,
    )

with right_column:

    st.write("Months to include")

    months_row_1 = [
        calendar.month_name[m] for m in range(1, 7)
    ]

    months_row_2 = [
        calendar.month_name[m] for m in range(7, 13)
    ]

    selected_row_1 = st.pills(
        "Months 1 to 6",
        options=months_row_1,
        selection_mode="multi",
        default=[],
        label_visibility="collapsed",
        key="months_row_1",
    )

    selected_row_2 = st.pills(
        "Months 7 to 12",
        options=months_row_2,
        selection_mode="multi",
        default=[],
        label_visibility="collapsed",
        key="months_row_2",
    )

    selected_months_names = selected_row_1 + selected_row_2

    selected_months = [
        month
        for month in range(1, 13)
        if calendar.month_name[month] in selected_months_names
    ]

try:
    flow_data = load_flows_for_year(
        mongo_uri,
        selected_connection,
        selected_year,
    )
except OperationFailure as error:
    if error.code == 18 or "authentication failed" in str(error).lower():
        st.error(
            "MongoDB Atlas rejected the database credentials. Verify the "
            "configured MongoDB database user and password."
        )
    else:
        st.error(f"Unable to retrieve the selected flow records from MongoDB: {error}")
    st.stop()
except PyMongoError as error:
    st.error(f"Unable to retrieve the selected flow records from MongoDB: {error}")
    st.stop()

if flow_data.empty:
    st.info("No flow records are available for this connection and year.")
else:
    with left_column:
        st.subheader(f"Direction shares in {selected_year}")

        annual_data = flow_data.copy()
        # Ensure timestamps are datetime objects
        annual_data["timestamp"] = pd.to_datetime(annual_data["timestamp"])

        # Sort measurements chronologically within each direction
        annual_data = annual_data.sort_values(
            ["from_zone", "to_zone", "timestamp"]
        ).copy()

        # Calculate the duration until the next measurement, in hours
        annual_data["duration_hours"] = (
            annual_data.groupby(["from_zone", "to_zone"])["timestamp"]
            .shift(-1)
            .sub(annual_data["timestamp"])
            .dt.total_seconds()
            / 3600
        )

        # Remove invalid intervals
        annual_data.loc[
            annual_data["duration_hours"] <= 0,
            "duration_hours"
        ] = float("nan")

        # Convert power (MW) into estimated energy (MWh)
        annual_data["energy_mwh"] = (
            annual_data["flow_mw"] * annual_data["duration_hours"]
        )

        # Exclude measurements for which the duration is unknown
        valid_data = annual_data.dropna(subset=["energy_mwh"]).copy()

        # Calculate total signed energy for each direction
        energy_by_direction = valid_data.groupby(
            ["from_zone", "to_zone"]
        )["energy_mwh"].sum()

        # Use absolute values for the pie chart
        pie_values = energy_by_direction.abs()

        if pie_values.empty or pie_values.sum() == 0:
            st.info("There is no measurable energy flow to display for this year.")
        else:
            labels = [
                f"{from_zone} → {to_zone}"
                for from_zone, to_zone in energy_by_direction.index
            ]
            # Create interactive pie chart
            fig = go.Figure(
                data=[
                    go.Pie(
                    labels=labels,
                    values=pie_values.values,
                    hole=0.4,
                    textinfo="label+percent",
                    marker=dict(
                        colors=[
                            PLOTLY_COLORS["secondary"]
                            if "NO_" in label.split(" → ")[0]
                            else PLOTLY_COLORS["electricity"]
                            for label in labels
                        ]
                    ),
                    hovertemplate=(
                        "%{label}<br>"
                        "Energy: %{value:,.2f} MWh<br>"
                        "Share: %{percent}"
                        "<extra></extra>"
                    )
                )
                ]
            )

            fig = apply_plotly_theme(fig)

            fig.update_layout(
                title=dict(
                    text="Energy share by direction",
                    x=0.5
                ),
                showlegend=True,
                height=550,
                hovermode="closest"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )
            st.caption(
                "Shares are calculated from the absolute signed energy totals. "
                "Energy is estimated by multiplying each power measurement (MW) "
                "by the elapsed time until the next measurement. "
                "This assumes constant power between consecutive timestamps."
            )       

    with right_column:
        st.subheader(f"Physical flows in {selected_year}")
        if not selected_months:
            st.info("Select at least one month to display the flow time series.")
        else:
            month_data = flow_data[
                flow_data["timestamp"].dt.month.isin(selected_months)
            ].copy()
            if month_data.empty:
                st.info("No records are available for the selected months.")
            else:
                month_data["timestamp"] = month_data["timestamp"].dt.tz_convert(
                    "Europe/Oslo"
                )
                # Create interactive time series chart
                fig = go.Figure()

                for (from_zone, to_zone), direction_data in month_data.groupby(
                    ["from_zone", "to_zone"]
                ):

                    direction_data = direction_data.sort_values("timestamp")

                    fig.add_trace(
                    go.Scatter(
                        x=direction_data["timestamp"],
                        y=direction_data["flow_mw"],
                        mode="lines",
                        name=f"{from_zone} → {to_zone}",
                        line=dict(
                            width=1.2,
                            color=(
                                PLOTLY_COLORS["secondary"]
                                if from_zone.startswith("NO_")
                                else PLOTLY_COLORS["electricity"]
                            )
                        ),
                        hovertemplate=(
                            "Date: %{x|%d/%m/%Y %H:%M}<br>"
                            "Physical flow: %{y:.2f} MW"
                            "<extra></extra>"
                        )
                    )
                )

                fig = apply_plotly_theme(fig)

                fig.update_layout(
                    title=dict(
                        text="Physical electricity flows",
                        x=0.5,
                        xanchor="center",
                        font=dict(size=18)
                    ),
                    margin=dict(
                        l=50,
                        r=30,
                        t=70,
                        b=50
                    ),
                    xaxis_title="Date and time",
                    yaxis_title="Physical flow (MW)",
                    legend_title="Direction",
                    height=650
                )
                st.caption(
                    f"Connection: {selected_connection[0]} ↔ {selected_connection[1]}"
                )
                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

with st.expander("About these data"):
    st.write(
        "The measurements are read from the project's MongoDB collection "
        "`energy_database.crossborder_flows`. The collection contains "
        "cross-border physical-flow data sourced from the ENTSO-E "
        "Transparency Platform. Power measurements are stored in MW. "
        "Although measurements are generally available at 15-minute "
        "intervals, some connections contain longer intervals. "
        "For the annual energy-share chart, energy is estimated by "
        "multiplying each power measurement by the elapsed time until "
        "the next measurement, assuming constant power over that interval. "
        "The final measurement in each direction is excluded because "
        "its interval duration cannot be determined from the available data."
    )
