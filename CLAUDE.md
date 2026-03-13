# CLAUDE.md - Project Notes

## Project Overview

**raprock** - Neorock rapid response observation tools

Goal: Monitor Near Earth Objects (NEOs) and find close observation opportunities for an array of observatories.

## Data Provider

**NEOScan** - ESA facility (operated by SpaceDyS)
- Website: https://newton.spacedys.com/neodys/NEOScan/index_neocp.html
- Provides real-time list of NEO objects
- Offers ephemeris computation for each object
- No official API available - using web scraping/requests

## Current Implementation

### Module: `raprock/pipes.py`

Filtering and aggregation pipeline operating on ephemeris DataFrames.

**Filter functions** (each returns a filtered DataFrame):
- `after_twilight(df, phase)` — keep rows where Sun elevation is below the given twilight threshold (civil/nautical/astronomical)
- `not_moon_occulted(df)` — keep rows where the object is outside 2× the Moon's angular radius
- `higher_than(df, deg)` — keep rows where object altitude exceeds `deg` degrees
- `longer_than(df, duration_min)` — keep only rows belonging to contiguous windows spanning ≥ `duration_min` minutes

**Aggregation / window utilities:**
- `compact_intervals(idx)` — returns `(starts, ends)` index arrays marking boundaries of contiguous index groups
- `split(df)` — splits df into a list of sub-DataFrames, one per contiguous window
- `opportunity_windows(df, exposure_len)` — aggregates filtered rows into a summary table; one row per window that can fit an exposure of `exposure_len` minutes, with columns `win_start`, `win_end`, `Alt_max`, `V_min`, `V_delta`
- `start_observation_between(df, exposure_min)` — returns `(start_mjd, end_mjd)` tuples giving the valid start interval per window

---

### Module: `raprock/neoscan.py`

**Main Function: `post_ephemeris_request(payload: dict, headers: dict) -> str`**
- Location: raprock/neoscan.py:26
- Purpose: Retrieve ephemeris data for a specific NEO object

**Implementation Details:**
1. **Anubis PoW Challenge Handler**
   - NEOScan uses Anubis anti-bot protection
   - Solves SHA256 proof-of-work puzzles (difficulty varies)
   - Functions:
     - `extract_anubis_challenge()` - Parses challenge from HTML
     - `solve_pow()` - Brute-force hash with required prefix
     - `accept_anubis_challenge()` - Submits solution, gets auth cookie

2. **Ephemeris Request Flow**
   - POST to: `https://newton.spacedys.com/neodys/include/neodys_cgi-bin/nom_ephem.pl`
   - Payload includes:
     - `any_name`: Object designation (e.g., "C1C9Y25")
     - `code`: Observatory MPC code (e.g., "500" for geocenter)
     - Time range: year0/month0/day0/hour0/mins0 to year1/month1/day1/hour1/mins1
     - `interval` + `intunit`: Step size (e.g., "1.0" "hours")
   - Response: HTML page with link to `.eph` file
   - Downloads and returns raw ASCII ephemeris data

## Dependencies

- `astropy>=7.2.0` - Astronomy calculations
- `bs4>=0.0.2` - HTML parsing
- `pandas>=3.0.1` - Data structures
- `requests>=2.32.5` - HTTP client

Dev dependencies:
- `pytest>=9.0.2`

## Project Structure

```
raprock/
├── raprock/
│   ├── __init__.py
│   ├── neoscan.py       # NEOScan ephemeris retrieval
│   ├── pipes.py         # Filtering & aggregation pipeline
│   └── utils.py         # Constants and unit conversions
├── tests/
│   └── __init__.py
├── main.py              # Entry point (placeholder)
├── pyproject.toml       # Project configuration
└── README.md            # (empty)
```

## TODO / Future Work

### Core Features Needed
1. **NEO List Retrieval**
   - Scrape/parse NEO list from NEOScan index page
   - Extract object designations and basic parameters

2. **Ephemeris Parsing**
   - Parse .eph ASCII format
   - Extract positions, velocities, magnitudes, etc.

3. **Observatory Configuration**
   - Define observatory array (locations, instruments)
   - MPC observatory codes
   - Horizon/weather constraints

4. **Visibility Analysis**
   - Calculate altitude/azimuth for each observatory
   - Apply visibility constraints (min altitude, sun separation, etc.)
   - Identify observation windows

5. **Opportunity Ranking**
   - Score opportunities by:
     - Object brightness
     - Altitude/airmass
     - Time window duration
     - Observational priority

6. **Alert/Reporting System**
   - Generate observation schedules
   - Alert when high-priority opportunities appear

## Notes

- NEOScan requires solving PoW challenges, adds ~1-2 second delay per request
- Current implementation tested with example object "C1C9Y25"
- Observatory code "500" = geocenter (for testing)
- Time range in example: 2026-02-24 to 2026-03-25, 1-hour intervals

## Code Style Preferences

**Comments**: Use sparingly. Prioritize clear, self-documenting code. Only add comments when:
- Code clarity cannot be achieved through better naming/structure
- Explaining _why_ something is done (not what)
- Warning about pesky passages that should be improved later

Do not comment obvious operations or repeat what the code already says.

## Development Status

- [x] Ephemeris retrieval working
- [x] NEO list scraping (get_neocp_objects)
- [x] Ephemeris parsing (parse_ephemeris)
- [ ] Observatory configuration
- [ ] Visibility calculations
- [x] Opportunity detection (opportunity_windows in pipes.py)
- [ ] Testing suite (partial — pipes covered, neoscan not yet)
