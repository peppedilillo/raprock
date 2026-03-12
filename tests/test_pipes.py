import pandas as pd
import pytest

from raprock.pipes import (
    TWILIGHTS,
    after_twilight,
    compact_intervals,
    higher_than,
    longer_than,
    start_observation_between,
)
from raprock.utils import min2days

STEP = 15 * min2days  # 15-minute steps in days


@pytest.fixture
def two_window_df():
    """
    10 rows at 15-min intervals. Two contiguous windows after filtering by altitude:
      Window A: original index 0–2 (3 rows, ~30 min span)
      Window B: original index 5–9 (5 rows, ~60 min span)
    Rows 3–4 have low altitude, so they break the continuity.
    """
    n = 10
    mjd_base = 60000.0
    mjds = [mjd_base + i * STEP for i in range(n)]
    alts = [30.0] * 3 + [5.0, 5.0] + [30.0] * 5
    sun_elevs = [-20.0] * n

    df = pd.DataFrame({"MJD": mjds, "Alt": alts, "Sun_elev": sun_elevs})
    return df


@pytest.fixture
def filtered_df(two_window_df):
    """Apply higher_than to expose the two-window structure."""
    return higher_than(two_window_df, 10.0)


@pytest.mark.parametrize("phase,threshold", list(TWILIGHTS.items()))
def test_after_twilight(phase, threshold):
    df = pd.DataFrame({
        "MJD": [1.0, 2.0, 3.0],
        "Alt": [30.0, 30.0, 30.0],
        "Sun_elev": [threshold - 1, threshold, threshold + 1],
    })
    result = after_twilight(df, phase=phase)
    assert len(result) == 1
    assert result.iloc[0]["Sun_elev"] == threshold - 1


def test_higher_than(two_window_df):
    result = higher_than(two_window_df, 10.0)
    assert len(result) == 8
    assert all(result["Alt"] > 10.0)


def test_compact_intervals(filtered_df):
    starts, ends = compact_intervals(filtered_df.index)
    assert list(starts) == [0, 5]
    assert list(ends) == [2, 9]


def test_longer_than_excludes_short(filtered_df):
    # Window A spans 2 * STEP = 30 min, Window B spans 4 * STEP = 60 min
    # With threshold 45 min, only Window B should pass
    result = longer_than(filtered_df, duration_min=45)
    assert set(result.index) == {5, 6, 7, 8, 9}


def test_longer_than_keeps_all(filtered_df):
    result = longer_than(filtered_df, duration_min=25)
    assert set(result.index) == {0, 1, 2, 5, 6, 7, 8, 9}


def test_start_observation_between(filtered_df):
    # Window A: span = 30 min, Window B: span = 60 min
    # exposure_min=20: Window A valid (30 > 20), Window B valid (60 > 20)
    windows = start_observation_between(filtered_df, exposure_min=20)
    assert len(windows) == 2

    mjd_a_start = filtered_df.loc[0].MJD
    mjd_a_end = filtered_df.loc[2].MJD - 20 * min2days
    assert abs(windows[0][0] - mjd_a_start) < 1e-10
    assert abs(windows[0][1] - mjd_a_end) < 1e-10


def test_start_observation_between_window_too_short(filtered_df):
    # exposure_min=35: Window A (30 min) is too short, only Window B passes
    windows = start_observation_between(filtered_df, exposure_min=35)
    assert len(windows) == 1
    assert abs(windows[0][0] - filtered_df.loc[5].MJD) < 1e-10
