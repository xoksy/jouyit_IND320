import numpy as np
import pandas as pd
import plotly.graph_objects as go

from plotly.subplots import make_subplots
from scipy.signal import spectrogram
from statsmodels.tsa.seasonal import STL


# --------------------------------------------------
# STL DECOMPOSITION
# --------------------------------------------------

def plot_stl_decomposition(
    data,
    seasonal=13,
    trend=53,
    robust=True,
    period=52
):
    """
    Perform STL decomposition on reservoir filling degree.
    Returns an interactive Plotly figure.
    """

    # 1. Prepare the time series
    filling_series = (
        data.set_index("date_id")["filling_degree"]
        .sort_index()
    )

    # 2. Check data and parameters
    if filling_series.empty or filling_series.isna().any():
        raise ValueError(
            "The filling degree series is empty or contains missing values."
        )

    if seasonal < 7 or seasonal % 2 == 0:
        raise ValueError(
            "seasonal must be an odd integer >= 7."
        )

    if trend <= period or trend % 2 == 0:
        raise ValueError(
            "trend must be odd and greater than period."
        )

    # 3. Perform STL decomposition
    stl = STL(
        filling_series,
        period=period,
        seasonal=seasonal,
        trend=trend,
        robust=robust
    )

    stl_result = stl.fit()

    # 4. Create interactive subplots
    figure = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        subplot_titles=(
            "Observed",
            "Trend",
            "Seasonal",
            "Residual"
        )
    )

    components = [
        ("Observed", stl_result.observed),
        ("Trend", stl_result.trend),
        ("Seasonal", stl_result.seasonal),
        ("Residual", stl_result.resid),
    ]

    for row, (name, component) in enumerate(components, start=1):

        figure.add_trace(
            go.Scatter(
                x=component.index,
                y=component.values,
                mode="lines",
                name=name,
                line=dict(width=1.5),
                hovertemplate=(
                    "Date: %{x|%d %b %Y}<br>"
                    f"{name}: " + "%{y:.3f}"
                    "<extra></extra>"
                )
            ),
            row=row,
            col=1
        )

    # 5. Layout
    figure.update_layout(
        title={
            "text": "STL decomposition — Reservoir filling degree",
            "x": 0.5,
            "xanchor": "center"
        },
        height=850,
        showlegend=False,
        hovermode="x unified",
        template="plotly_white",
        margin=dict(l=60, r=30, t=90, b=50)
    )

    figure.update_xaxes(
        title_text="Date",
        row=4,
        col=1
    )

    figure.update_yaxes(
        title_text="Filling degree",
        row=1,
        col=1
    )

    figure.update_yaxes(
        title_text="Trend",
        row=2,
        col=1
    )

    figure.update_yaxes(
        title_text="Seasonal",
        row=3,
        col=1
    )

    figure.update_yaxes(
        title_text="Residual",
        row=4,
        col=1
    )

    return figure


# --------------------------------------------------
# SPECTROGRAM
# --------------------------------------------------

def plot_spectrogram(
    data,
    window_length=52,
    window_overlap=26
):
    """
    Create an interactive spectrogram of reservoir filling degree.
    Returns a Plotly figure.
    """

    # 1. Prepare the time series
    filling_series = (
        data.set_index("date_id")["filling_degree"]
        .sort_index()
    )

    values = filling_series.to_numpy()

    # 2. Check data and parameters
    if len(values) < 2 or not np.isfinite(values).all():
        raise ValueError(
            "The series must contain at least two valid observations."
        )

    if window_length <= 0 or window_length > len(values):
        raise ValueError("Invalid window_length.")

    if window_overlap < 0 or window_overlap >= window_length:
        raise ValueError(
            "window_overlap must be smaller than window_length."
        )

    # 3. Compute the spectrogram
    frequencies, times, power = spectrogram(
        values,
        fs=1,
        nperseg=window_length,
        noverlap=window_overlap
    )

    # 4. Convert relative time positions into dates
    dates = (
        filling_series.index[0]
        + pd.to_timedelta(times, unit="W")
    )

    # 5. Convert power into decibels
    power_db = 10 * np.log10(power + 1e-12)

    # 6. Create interactive heatmap
    figure = go.Figure(
        data=go.Heatmap(
            x=dates,
            y=frequencies,
            z=power_db,
            colorscale="Viridis",
            colorbar=dict(
                title="Power spectral<br>density (dB)"
            ),
            hovertemplate=(
                "Date: %{x|%d %b %Y}<br>"
                "Frequency: %{y:.4f} cycles/week<br>"
                "Power: %{z:.2f} dB"
                "<extra></extra>"
            )
        )
    )

    # 7. Layout
    figure.update_layout(
        title={
            "text": "Spectrogram — Reservoir filling degree",
            "x": 0.5,
            "xanchor": "center"
        },
        xaxis_title="Date",
        yaxis_title="Frequency (cycles per week)",
        height=600,
        template="plotly_white",
        margin=dict(l=60, r=60, t=80, b=50)
    )

    return figure