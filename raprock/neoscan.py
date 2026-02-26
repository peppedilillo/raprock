import hashlib
from io import StringIO
import json
import re
import time
import urllib.parse
from datetime import datetime, timedelta

from astropy.time import Time
from bs4 import BeautifulSoup
import pandas as pd
import requests

from raprock.observatories import Observatory

BASE_URL = "https://newton.spacedys.com"
TARGET_URL = f"{BASE_URL}/neodys/include/neodys_cgi-bin/nom_ephem.pl"
NEOCP_INDEX_URL = f"{BASE_URL}/neodys/NEOScan/index_neocp.html"


def get_objects() -> tuple[str, ...]:
    """
    Fetch the current list of NEOCP objects from NEOScan.
    Returns a pandas DataFrame with all NEO objects and their properties.
    """
    session = requests.Session()
    resp = session.get(NEOCP_INDEX_URL, timeout=10)
    resp.raise_for_status()
    return _parse_neocp_table(resp.text)


def get_ephemeris(
    object_name: str,
    observatory: Observatory,
    tstart: datetime | str,
    tend: datetime | str,
    deltat: timedelta | float,
) -> pd.DataFrame:
    """
    Fetch and parse ephemeris data for a NEOCP object.

    Args:
        object_name: Object designation (e.g. "C1C9Y25").
        observatory: Observatory instance; its MPC code is used for the request.
        tstart: Start of the time window (datetime or ISO 8601 string, e.g, "2026-10-17 18:00").
        tend: End of the time window (datetime or ISO 8601 string, e.g. "2026-12-22 18:00").
        deltat: Step size as a timedelta or as a float number of minutes.

    Returns:
        DataFrame with columns MJD, RA_deg, DEC_deg, rates, magnitudes, etc.
    """
    if isinstance(tstart, str):
        tstart = datetime.fromisoformat(tstart)
    if isinstance(tend, str):
        tend = datetime.fromisoformat(tend)

    total_minutes = deltat.total_seconds() / 60 if isinstance(deltat, timedelta) else float(deltat)

    payload = {
        "any_name": object_name,
        "code": observatory.code,
        "year0": str(tstart.year),
        "month0": f"{tstart.month:02d}",
        "day0": f"{tstart.day:02d}",
        "hour0": f"{tstart.hour:02d}",
        "mins0": f"{tstart.minute:02d}",
        "year1": str(tend.year),
        "month1": f"{tend.month:02d}",
        "day1": f"{tend.day:02d}",
        "hour1": f"{tend.hour:02d}",
        "mins1": f"{tend.minute:02d}",
        "interval": str(total_minutes),
        "intunit": "minutes",
    }
    return _parse_ephemeris(_post_ephemeris_request(payload))
    

def _parse_neocp_table(html: str) -> tuple[str]:
    """
    Returns a tuple of NEOCP object names.
    """
    # pandas.read_html returns a list of all tables found in the HTML
    tables = pd.read_html(StringIO(html))
    if not tables:
        raise RuntimeError("No tables found in HTML")
    df = tables[0]
    df.columns = df.columns.str.strip()
    return tuple(df["NEOCP name"])

def _post_ephemeris_request(payload: dict) -> str:
    """
    Anubis → POST form → extract .eph link → download file.
    Returns the raw text of the .eph ASCII file.
    """
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
    }

    def extract_anubis_challenge(html: str) -> dict | None:
        soup = BeautifulSoup(html, "html.parser")
        tag = soup.find("script", {"id": "anubis_challenge"})
        return json.loads(tag.string.strip()) if tag else None

    def solve_pow(random_data: str, difficulty: int) -> tuple[int, str, float]:
        prefix = "0" * difficulty
        start = time.time()
        for nonce in range(10_000_000):
            digest = hashlib.sha256(f"{random_data}{nonce}".encode()).hexdigest()
            if digest.startswith(prefix):
                return nonce, digest, time.time() - start
        raise RuntimeError(
            f"PoW unsolvable at difficulty={difficulty} within 10M iterations"
        )

    def accept_anubis_challenge(
        session: requests.Session, challenge_data: dict
    ) -> bool:
        rules = challenge_data["rules"]
        challenge = challenge_data["challenge"]
        algorithm = rules.get("algorithm", "fast")
        difficulty = rules.get("difficulty", 4)
        ch_id = challenge["id"]
        rand_data = challenge["randomData"]

        if algorithm not in ("fast", "slow"):
            raise NotImplementedError(f"Unknown Anubis algorithm: {algorithm!r}")

        nonce, digest, elapsed = solve_pow(rand_data, difficulty)
        pass_url = (
            f"{BASE_URL}/.within.website/x/cmd/anubis/api/pass-challenge"
            f"?response={digest}&nonce={nonce}&redir=/&elapsedTime={int(elapsed * 1000)}&id={ch_id}"
        )
        session.get(pass_url, headers=HEADERS, allow_redirects=True, timeout=30)

        auth_cookie = next(
            (
                v
                for k, v in session.cookies.items()
                if "anubis-auth" in k and "verification" not in k
            ),
            None,
        )
        if auth_cookie:
            return True
        return False

    session = requests.Session()

    # solve anubis pow problem
    resp = session.get(TARGET_URL, headers=HEADERS, timeout=10)
    challenge = extract_anubis_challenge(resp.text)
    if challenge:
        accept_anubis_challenge(session, challenge)

    # post ephemeris request
    resp = session.post(
        TARGET_URL,
        data=payload,
        headers={**HEADERS, "Referer": TARGET_URL, "Origin": BASE_URL},
        timeout=30,
    )
    resp.raise_for_status()

    # retrieve table
    soup = BeautifulSoup(resp.text, "html.parser")
    link_tag = soup.find("a", download=True, href=lambda h: h and h.endswith(".eph"))
    if not link_tag:
        raise RuntimeError("Could not find .eph download link in the response HTML.")

    eph_href = link_tag["href"]  # e.g. ./nom_ephem/85331.eph
    eph_url = urllib.parse.urljoin(TARGET_URL, eph_href)
    eph_resp = session.get(eph_url, headers=HEADERS, timeout=30)
    eph_resp.raise_for_status()
    return eph_resp.text


class EphFormatError(Exception):
    """The ephemeris table is in an unexpected format."""


class EphEmptyError(Exception):
    """The ephemeris table bears no data."""


def _parse_ephemeris(eph_text: str) -> pd.DataFrame:
    """
    Parse ephemeris text from NEOScan into a pandas DataFrame.

    Converts RA/DEC from HMS/DMS to degrees, dates to MJD, and angular rates to degrees.
    Returns DataFrame with numeric values ready for computation.
    """

    def _split_hms_dms(start: int, end: int) -> list[tuple[int, int]]:
        """
        Split an RA or DEC separator group into 3 sub-fields.

        Both RA (" hh mm ss.sss") and DEC ("±dd mm ss.ss") follow the same
        internal layout: 3-char field, space, 2-char field, space, remainder.
        """
        return [
            (start, start + 3),
            (start + 4, start + 6),
            (start + 7, end),
        ]

    def _colspecs_from_separator(sep_line: str) -> list[tuple[int, int]]:
        """
        Derive column specs from the '====...' separator line.

        Groups 0+1 (Date + Hour) merge into a single Datetime column.
        Group 2 (RA) splits into h, m, s sub-fields.
        Group 3 (DEC) splits into d, ', " sub-fields.
        Groups 4-23 map 1:1 to the remaining columns.
        """
        groups = [(m.start(), m.end()) for m in re.finditer(r"=+", sep_line)]
        if len(groups) != 24:
            raise EphFormatError(
                f"Expected 24 column groups in separator, found {len(groups)}"
            )

        # Datetime: merge groups 0 (Date) and 1 (Hour)
        dt_start = groups[0][0]
        dt_end = groups[1][1]

        ra_subs = _split_hms_dms(*groups[2])
        dec_subs = _split_hms_dms(*groups[3])

        colspecs = [(dt_start, dt_end)] + ra_subs + dec_subs
        for g in groups[4:]:
            colspecs.append(g)

        return colspecs

    lines = eph_text.split("\n")

    sep_line_idx = None
    for i, line in enumerate(lines):
        if "===" in line:
            sep_line_idx = i
            break
    if sep_line_idx is None:
        raise EphFormatError("Could not find separator line ('===')")

    data_start_idx = sep_line_idx + 1
    colspecs = _colspecs_from_separator(lines[sep_line_idx])

    data_text = "\n".join(lines[data_start_idx:])
    if not any(c.isdigit() for c in data_text):
        raise EphEmptyError(
            f"The table does not contain numeric characters. "
            f"Table content:\n\n"
            f"{data_text}"
        )

    df = pd.read_fwf(
        StringIO(data_text),
        colspecs=colspecs,
        names=[
            "Datetime",
            "RA_h",
            "RA_m",
            "RA_s",
            "DEC_d",
            "DEC_m",
            "DEC_s",
            "Mag",
            "Alt",
            "Azi",
            "Airmass",
            "Sun_elev",
            "SolEl",
            "LunEl",
            "LunPh",
            "Phase",
            "Glat",
            "Glon",
            "R",
            "Delta",
            "RA_rate",
            "DEC_rate",
            "Vel",
            "PA",
            "Err1",
            "Err2",
            "PA_err",
        ],
        dtype={"DEC_d": str},
        header=None,
    )

    df["RA_deg"] = (df["RA_h"] + df["RA_m"] / 60.0 + df["RA_s"] / 3600.0) * 15.0
    dec_sign = df["DEC_d"].str.strip().str.startswith("-").map({True: -1, False: 1})
    df["DEC_deg"] = dec_sign * (
            pd.to_numeric(df["DEC_d"], errors="coerce").abs()
            + df["DEC_m"] / 60.0
            + df["DEC_s"] / 3600.0
    )
    df["MJD"] = Time(pd.to_datetime(df["Datetime"]).tolist(), format="datetime", scale="utc").mjd
    df["RA_rate_deg"] = df["RA_rate"] / 3600.0
    df["DEC_rate_deg"] = df["DEC_rate"] / 3600.0
    df["Vel_deg"] = df["Vel"] / 3600.0
    df = df.drop(
        columns=[
            "Datetime",
            "RA_h",
            "RA_m",
            "RA_s",
            "DEC_d",
            "DEC_m",
            "DEC_s",
            "RA_rate",
            "DEC_rate",
            "Vel",
            "PA",
            "Err1",
            "Err2",
            "PA_err",
        ]
    )
    return df
