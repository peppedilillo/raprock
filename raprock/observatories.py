from typing import NamedTuple


class Observatory(NamedTuple):
    name: str
    code: str


LBT = Observatory("LBT", "G83")
