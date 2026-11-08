import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from scipy.signal import spectrogram
from statsmodels.tsa.seasonal import STL

#Add the two functions use in the notebook
def plot_stl_decomposition(
    data,
    seasonal=13,
    trend=53,
    robust=True,
    period=52
):
    """
    Perform STL decomposition on reservoir filling degree.
    Returns the decomposition plot.
    """

    # Prepare the time series
    filling_series = (
        data.set_index("date_id")["filling_degree"]
        .sort_index()
    )

    # Check data and parameters
    if filling_series.empty or filling_series.isna().any():
        raise ValueError("The filling degree series is empty or contains missing values.")

    if seasonal < 7 or seasonal % 2 == 0:
        raise ValueError("seasonal must be an odd integer >= 7.")

    if trend <= period or trend % 2 == 0:
        raise ValueError("trend must be odd and greater than period.")

    # Perform STL decomposition
    stl = STL(
        filling_series,
        period=period,
        seasonal=seasonal,
        trend=trend,
        robust=robust
    )

    stl_result = stl.fit()

    # Create decomposition plot
    figure = stl_result.plot()
    figure.set_size_inches(14, 9)

    figure.suptitle(
        "STL decomposition — Reservoir filling degree",
        fontsize=14,
        y=1.02
    )

    figure.tight_layout()

    return figure

def plot_spectrogram(
    data,
    window_length=52,
    window_overlap=26
):
    """
    Create a spectrogram of the reservoir filling degree.
    Returns the spectrogram plot.
    """

    # Prepare the time series
    filling_series = (
        data.set_index("date_id")["filling_degree"]
        .sort_index()
    )

    values = filling_series.to_numpy()

    # Check data and parameters
    if len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("The series must contain at least two valid observations.")

    if window_length <= 0 or window_length > len(values):
        raise ValueError("Invalid window_length.")

    if window_overlap < 0 or window_overlap >= window_length:
        raise ValueError("window_overlap must be smaller than window_length.")

    # Compute the spectrogram
    frequencies, times, power = spectrogram(
        values,
        fs=1,
        nperseg=window_length,
        noverlap=window_overlap
    )

    # Convert relative time positions into dates
    dates = (
        filling_series.index[0]
        + pd.to_timedelta(times, unit="W")
    )

    # Plot the spectrogram
    figure, axis = plt.subplots(figsize=(14, 6))

    mesh = axis.pcolormesh(
        dates,
        frequencies,
        10 * np.log10(power + 1e-12),
        shading="auto",
        cmap="viridis"
    )

    axis.set_title("Spectrogram — Reservoir filling degree")
    axis.set_xlabel("Date")
    axis.set_ylabel("Frequency (cycles per week)")

    figure.colorbar(
        mesh,
        ax=axis,
        label="Power spectral density (dB)"
    )

    figure.tight_layout()

    return figure