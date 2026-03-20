from typing import NamedTuple


class Observatory(NamedTuple):
    name: str
    code: str


LBT = Observatory("LBT", "G83")
VST = Observatory("VST", "309")
CASSINI = Observatory("CASSINI", "598")
