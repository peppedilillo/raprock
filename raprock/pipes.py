import numpy as np
import pandas as pd

from raprock.utils import min2days
from raprock.utils import MOON_RADIUS_DEG
from raprock.utils import TWILIGHTS


def after_twilight(df: pd.DataFrame, phase: str = "astronomical") -> pd.DataFrame:
    """Filter rows to those after the given twilight phase (civil/nautical/astronomical)."""
    return df[df["Sun_elev"] < TWILIGHTS[phase]]


def not_moon_occulted(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Filter rows where the object is outside twice the Moon's angular radius from the lunar center."""
    return df[df["LunEl"].abs() > 2.0 * MOON_RADIUS_DEG]


def higher_than(df: pd.DataFrame, deg: float) -> pd.DataFrame:
    """Filter rows to those where object altitude exceeds deg degrees."""
    return df[df["Alt"] > deg]


def longer_than(df: pd.DataFrame, duration_min: float) -> pd.DataFrame:
    """Keeps only rows belonging to contiguous windows >= duration_min minutes."""
    starts, ends = compact_intervals(df.index)
    mask = np.zeros(len(df.index), dtype=bool)
    for s, e in zip(starts, ends):
        if df.loc[e].MJD - df.loc[s].MJD > duration_min * min2days:
            mask |= (df.index >= s) & (df.index <= e)
    return df[mask]


def compact_intervals(idx: pd.Index) -> tuple[np.ndarray, np.ndarray]:
    """Return (starts, ends) index arrays marking boundaries of contiguous index groups."""
    starts = idx[(np.diff(idx, prepend=-np.inf) - 1.0) > 1.0]
    ends = idx[-np.diff(idx[::-1], prepend=np.inf)[::-1] > 1.0]
    return starts, ends


def split(df: pd.DataFrame) -> list[pd.DataFrame]:
    """Split df into a list of sub-DataFrames, one per contiguous index group."""
    starts, ends = compact_intervals(df.index)
    return [df.loc[s:e, :] for s, e in zip(starts, ends)]


def opportunity_windows(df: pd.DataFrame, exposure_len: float) -> pd.DataFrame:
    """Aggregate filtered ephemeris rows into one row per valid observation window.

    A window is valid only if it can accommodate an exposure of `exposure_len` minutes,
    i.e. win_end (= last MJD − exposure_len) is strictly greater than win_start.

    Returns a DataFrame with columns: Object, Obs_name, Obs_code, win_start, win_end,
    Alt_max (peak altitude), V_min (brightest magnitude), V_delta (magnitude swing).
    """
    rows = []
    for window in split(df):
        win_start = window["MJD"].iloc[0]
        win_end = window["MJD"].iloc[-1] - exposure_len * min2days
        if win_end <= win_start:
            continue
        rows.append({
            "Object":   window["Object"].iloc[0],
            "Obs_name": window["Obs_name"].iloc[0],
            "Obs_code": window["Obs_code"].iloc[0],
            "win_start": win_start,
            "win_end":   win_end,
            "Alt_max":  window["Alt"].max(),
            "V_min":    window["Mag"].min(),
            "V_delta":  window["Mag"].max() - window["Mag"].min(),
        })
    return pd.DataFrame(rows)


def start_observation_between(
    df: pd.DataFrame, exposure_min: float
) -> list[tuple[float, float]]:
    """For each contiguous window, returns the (start_mjd, end_mjd) interval within which
    an observation of exposure_min duration can begin and still finish before the window ends.
    """
    starts, ends = compact_intervals(df.index)
    windows: list[tuple[float, float]] = []
    for s, e in zip(starts, ends):
        exposure_days = exposure_min * min2days
        if (end_mjd := df.loc[e].MJD - exposure_days) - df.loc[s].MJD > 0.0:
            windows.append((df.loc[s].MJD.item(), end_mjd.item()))
    return windows
