import random
from dataclasses import dataclass


@dataclass(frozen=True)
class AIDelay:
    name: str        # i18n key
    seconds: float   # -1.0 表示随机

    def get_delay(self) -> float:
        if self.seconds < 0:
            return random.uniform(1.0, 5.0)
        return self.seconds


AI_DELAY_PRESETS = [
    AIDelay("ai_delay.1s",     1.0),
    AIDelay("ai_delay.3s",     3.0),
    AIDelay("ai_delay.5s",     5.0),
    AIDelay("ai_delay.random", -1.0),
]
