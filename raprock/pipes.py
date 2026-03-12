import pandas as pd
import numpy as np

from raprock.utils import min2days, TWILIGHTS, MOON_RADIUS_DEG


def after_twilight(df: pd.DataFrame, phase: str = "astronomical") -> pd.DataFrame:
    """Filter rows to those after the given twilight phase (civil/nautical/astronomical)."""
    return df[df["Sun_elev"] < TWILIGHTS[phase]]


def not_moon_occulted(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Filter rows where the object is outside twice the Moon's angular radius from the lunar center."""
    return df[df["LunEl"] > 2. * MOON_RADIUS_DEG]


def higher_than(df: pd.DataFrame, deg: float) -> pd.DataFrame:
    """Filter rows to those where object altitude exceeds deg degrees."""
    return df[df["Alt"] > deg]


def compact_intervals(idx: pd.Index) -> tuple[np.ndarray, np.ndarray]:
    """Return (starts, ends) index arrays marking boundaries of contiguous index groups."""
    starts = idx[(np.diff(idx, prepend=-np.inf) - 1.) > 1.]
    ends = idx[-np.diff(idx[::-1], prepend=np.inf)[::-1] > 1.]
    return starts, ends


def longer_than(df: pd.DataFrame, duration_min: float) -> pd.DataFrame:
    """Keeps only rows belonging to contiguous windows >= duration_min minutes."""
    starts, ends = compact_intervals(df.index)
    mask = np.zeros(len(df.index), dtype=bool)
    for s, e in zip(starts, ends):
        if df.loc[e].MJD - df.loc[s].MJD > duration_min * min2days:
            mask |= (df.index >= s) & (df.index <= e)
    return df[mask]


def start_observation_between(df: pd.DataFrame, exposure_min: float) -> list[tuple[float, float]]:
    """For each contiguous window, returns the (start_mjd, end_mjd) interval within which
    an observation of exposure_min duration can begin and still finish before the window ends."""
    starts, ends = compact_intervals(df.index)
    windows: list[tuple[float, float]] = []
    for s, e in zip(starts, ends):
        exposure_days = exposure_min * min2days
        if (end_mjd := df.loc[e].MJD - exposure_days) - df.loc[s].MJD > 0.:
            windows.append((df.loc[s].MJD.item(), end_mjd.item()))
    return windows
