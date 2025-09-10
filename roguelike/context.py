from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
import random


@dataclass
class GameContext:
    paused: bool = False
    levelup_choices: Optional[List[str]] = None
    rng: random.Random = field(default_factory=lambda: random.Random(2025))

