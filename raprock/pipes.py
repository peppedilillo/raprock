import numpy as np

from raprock.utils import min2days

TWILIGHTS = {
    "civil": -6.,
    "nautical": -12.,
    "astronomical": -18.,
}


def after_twilight(df, phase="astronomical"):
    """Filter rows to those after the given twilight phase (civil/nautical/astronomical)."""
    return df[df["Sun_elev"] < TWILIGHTS[phase]]


def higher_than(df, deg):
    """Filter rows to those where object altitude exceeds deg degrees."""
    return df[df["Alt"] > deg]


def compact_intervals(idx):
    """Return (starts, ends) index arrays marking boundaries of contiguous index groups."""
    starts = idx[(np.diff(idx, prepend=-np.inf) - 1.) > 1.]
    ends = idx[-np.diff(idx[::-1], prepend=np.inf)[::-1] > 1.]
    return starts, ends


def longer_than(df, duration_min):
    """Keeps only rows belonging to contiguous windows >= duration_min minutes."""
    starts, ends = compact_intervals(df.index)
    mask = np.zeros(len(df.index), dtype=bool)
    for s, e in zip(starts, ends):
        if df.loc[e].MJD - df.loc[s].MJD > duration_min * min2days:
            mask |= (df.index >= s) & (df.index <= e)
    return df[mask]


def start_observation_between(df, exposure_min):
    """For each contiguous window, returns the (start_mjd, end_mjd) interval within which
    an observation of exposure_min duration can begin and still finish before the window ends."""
    starts, ends = compact_intervals(df.index)
    windows = []
    for s, e in zip(starts, ends):
        exposure_days = exposure_min * min2days
        if (end_mjd := df.loc[e].MJD - exposure_days) - df.loc[s].MJD > 0.:
            windows.append((df.loc[s].MJD.item(), end_mjd.item()))
    return windows
