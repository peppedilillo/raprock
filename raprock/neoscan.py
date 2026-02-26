import hashlib
import json
import time
import urllib.parse

import requests
from bs4 import BeautifulSoup
import pandas as pd


BASE_URL   = "https://newton.spacedys.com"
TARGET_URL = f"{BASE_URL}/neodys/include/neodys_cgi-bin/nom_ephem.pl"


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}

def post_ephemeris_request(payload: dict, headers: dict=DEFAULT_HEADERS) -> str:
    """
    Anubis → POST form → extract .eph link → download file.
    Returns the raw text of the .eph ASCII file.
    """
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
        raise RuntimeError(f"PoW unsolvable at difficulty={difficulty} within 10M iterations")

    def accept_anubis_challenge(session: requests.Session, challenge_data: dict) -> bool:
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
        session.get(pass_url, headers=headers, allow_redirects=True, timeout=30)

        auth_cookie = next(
            (v for k, v in session.cookies.items() if "anubis-auth" in k and "verification" not in k),
            None,
        )
        if auth_cookie:
            return True
        return False


    session = requests.Session()

    # solve anubis pow problem
    resp = session.get(TARGET_URL, headers=headers, timeout=10)
    challenge = extract_anubis_challenge(resp.text)
    if challenge:
        accept_anubis_challenge(session, challenge)

    # post ephemeris request
    resp = session.post(
        TARGET_URL,
        data=payload,
        headers={**headers, "Referer": TARGET_URL, "Origin": BASE_URL},
        timeout=30,
    )
    resp.raise_for_status()

    # retrieve table
    soup = BeautifulSoup(resp.text, "html.parser")
    link_tag = soup.find("a", download=True, href=lambda h: h and h.endswith(".eph"))
    if not link_tag:
        raise RuntimeError("Could not find .eph download link in the response HTML.")

    eph_href = link_tag["href"]                       # e.g. ./nom_ephem/85331.eph
    eph_url  = urllib.parse.urljoin(TARGET_URL, eph_href)
    eph_resp = session.get(eph_url, headers=headers, timeout=30)
    eph_resp.raise_for_status()
    return eph_resp.text


if __name__ == "__main__":
    PAYLOAD = {
        "any_name": "C1C9Y25",
        "code": "500",
        "year0": "2026",
        "month0": "02",
        "day0": "24",
        "hour0": "15",
        "mins0": "00",
        "year1": "2026",
        "month1": "03",
        "day1": "25",
        "hour1": "15",
        "mins1": "00",
        "interval": "1.0",
        "intunit": "hours",
    }
    post_ephemeris_request(payload=PAYLOAD)

