# raprock

Rapid-response observation tools for Near Earth Objects.

## Setup

```bash
# if using pip
pip install .
# if using uv
uv sync
```

## Usage

```python
from raprock.neoscan import get_objects, get_ephemeris
from raprock.observatories import LBT

# List current NEOCP candidates
*_, last_object = get_objects()   # tuple of object names, e.g. ("X89330", "C1C9Y25", ...)

# Fetch ephemeris for one object
df = get_ephemeris(
    object_name=last_object,
    observatory=LBT,
    tstart="2026-02-26T18:00",
    tend="2026-03-10T18:00",
    deltat=30, # minutes
)
```

## Finding observation windows

### Filter pipeline

```python
from raprock.pipes import after_twilight, not_moon_occulted, higher_than, longer_than

EXPOSURE_MIN = 100  # minutes

filtered = (df
    .pipe(after_twilight, phase="nautical")   # sun below nautical twilight
    .pipe(not_moon_occulted)                  # object clear of the Moon
    .pipe(higher_than, deg=25)                # altitude > 25°
    .pipe(longer_than, duration_min=EXPOSURE_MIN)  # window long enough for exposure
)
```

### Aggregating into opportunity windows

```python
from raprock.pipes import opportunity_windows

windows = opportunity_windows(filtered, exposure_len=EXPOSURE_MIN)
```

### Multiple observatories

```python
from raprock.observatories import LBT, VST, CASSINI
import pandas as pd

dfs = {
    obs: get_ephemeris(object_name=last_object, observatory=obs,
                       tstart="2026-02-26T18:00", tend="2026-03-10T18:00",
                       deltat=30)
    for obs in [LBT, VST, CASSINI]
}

def filter_pipe(df):
    return (df
        .pipe(after_twilight, phase="nautical")
        .pipe(not_moon_occulted)
        .pipe(higher_than, deg=25)
        .pipe(longer_than, duration_min=EXPOSURE_MIN)
    )

all_windows = pd.concat([opportunity_windows(filter_pipe(d), EXPOSURE_MIN)
                         for d in dfs.values()])
```