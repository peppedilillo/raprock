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

### Fetch an ephemeris

```python
from raprock.neoscan import get_objects, get_ephemeris
from raprock.observatories import LBT

objects = get_objects()   # e.g. ("X89330", "C1C9Y25", ...)

df = get_ephemeris(
    object_name=objects[-1],
    observatory=LBT,
    tstart="2026-02-26T18:00",
    tend="2026-03-10T18:00",
    deltat=30, # minutes
)
```

## Finding observation windows

### Single observatory

```python
from raprock.neoscan import get_ephemeris
from raprock.observatories import LBT
from raprock.pipes import after_twilight, not_moon_occulted, higher_than, longer_than, opportunity_windows

EXPOSURE_MIN = 100  # minutes

df = get_ephemeris(
    object_name="CEC2XQ2",
    observatory=LBT,
    tstart="2026-03-12T18:00",
    tend="2026-03-16T18:00",
    deltat=15,
)

filtered = (df
    .pipe(after_twilight, phase="nautical")        # sun below nautical twilight
    .pipe(not_moon_occulted)                       # object clear of the Moon
    .pipe(higher_than, deg=25)                     # altitude > 25°
    .pipe(longer_than, duration_min=EXPOSURE_MIN)  # window long enough for exposure
)

# computes a dataframe with opportunity windows as rows
windows = opportunity_windows(filtered, exposure_len=EXPOSURE_MIN)
```

### Multiple observatories

```python
import pandas as pd
from raprock.neoscan import get_ephemeris
from raprock.observatories import LBT, VST, CASSINI
from raprock.pipes import after_twilight, not_moon_occulted, higher_than, longer_than, opportunity_windows

EXPOSURE_MIN = 100  # minutes

def filter_pipe(df):
    return (df
        .pipe(after_twilight, phase="nautical")
        .pipe(not_moon_occulted)
        .pipe(higher_than, deg=25)
        .pipe(longer_than, duration_min=EXPOSURE_MIN)
    )

dfs = {
    obs: get_ephemeris(
        object_name="CEC2XQ2",
        observatory=obs,
        tstart="2026-03-12T18:00",
        tend="2026-03-16T18:00",
        deltat=15,
    )
    for obs in [LBT, VST, CASSINI]
}

all_windows = pd.concat([opportunity_windows(filter_pipe(d), EXPOSURE_MIN)
                         for d in dfs.values()])
```

### Working with individual windows

`split()` gives direct access to the filtered rows of each contiguous window,
useful for computing custom statistics:

```python
from raprock.neoscan import get_ephemeris
from raprock.observatories import LBT
from raprock.pipes import after_twilight, higher_than, split

df = get_ephemeris(
    object_name="CEC2XQ2",
    observatory=LBT,
    tstart="2026-03-12T18:00",
    tend="2026-03-16T18:00",
    deltat=15,
)

filtered = df.pipe(after_twilight, phase="nautical").pipe(higher_than, deg=25)

for window in split(filtered):
    print(window["MJD"].iloc[0], window["Alt"].max())
```