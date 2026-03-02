"""Time control settings for human player turns (A+B format)."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TimeControl:
    """A+B time control: base_seconds per action + bank_seconds global pool."""

    name: str                         # i18n key, e.g. "tc.unlimited"
    base_seconds: Optional[int]       # None = unlimited
    bank_seconds: int = 0

    @property
    def is_unlimited(self) -> bool:
        return self.base_seconds is None


TIME_CONTROL_PRESETS = [
    TimeControl("tc.unlimited", None,  0),
    TimeControl("tc.5_20",       5,   20),
    TimeControl("tc.10_20",     10,   20),
    TimeControl("tc.15_30",     15,   30),
    TimeControl("tc.60_0",      60,    0),
]
