# raprock

Rapid-response observation tools for Near Earth Objects.

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
