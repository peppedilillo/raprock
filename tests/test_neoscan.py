from pathlib import Path

import pytest

from raprock.neoscan import _parse_ephemeris
from raprock.neoscan import _parse_neocp_table
from raprock.neoscan import EphEmptyError
from raprock.neoscan import EphFormatError

EPHEMERIS_DIR = Path(__file__).parent / "ephemeris"

# Errors raised intentionally by our parsing code — not bugs.
KNOWN_PARSE_ERRORS = (EphFormatError, EphEmptyError)


def test_parse_neocp_table():
    html = (Path(__file__).parent / "index_neocp.txt").read_text()
    objs = _parse_neocp_table(html)
    assert isinstance(objs, tuple)
    assert len(objs) > 0


def test_parse_ephemeris_values():
    """Regression test: spot-check known values from the reference file."""
    eph_text = (EPHEMERIS_DIR / "neoscan_ephemeris.txt").read_text()
    df = _parse_ephemeris(eph_text)

    assert len(df) == 649
    assert len(df.columns) == 19
    assert {
        "MJD",
        "RA_deg",
        "DEC_deg",
        "RA_rate_deg",
        "DEC_rate_deg",
        "Vel_deg",
    }.issubset(df.columns)

    assert df.iloc[0]["MJD"] == pytest.approx(61097.625, abs=0.001)
    assert df.iloc[0]["RA_deg"] == pytest.approx(155.506596, abs=0.001)
    assert df.iloc[0]["DEC_deg"] == pytest.approx(-0.825267, abs=0.001)

    assert df["RA_deg"].dtype == "float64"
    assert df["DEC_deg"].dtype == "float64"
    assert df["MJD"].dtype == "float64"


@pytest.mark.parametrize(
    "eph_file",
    sorted(EPHEMERIS_DIR.glob("*.txt")),
    ids=lambda p: p.stem,
)
def test_parse_ephemeris_file(eph_file):
    """Each file must either parse cleanly or raise one of our known errors."""
    eph_text = eph_file.read_text()

    try:
        df = _parse_ephemeris(eph_text)
    except KNOWN_PARSE_ERRORS:
        return

    assert df is not None
    assert len(df) > 0
    assert "MJD" in df.columns
    assert "RA_deg" in df.columns
    assert "DEC_deg" in df.columns
