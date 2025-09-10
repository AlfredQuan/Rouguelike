from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Set
import random
from typing import Any


@dataclass
class GameContext:
    paused: bool = False
    levelup_choices: Optional[List[str]] = None
    rng: random.Random = field(default_factory=lambda: random.Random(2025))
    meta_unlocked_subs: Set[str] = field(default_factory=set)
    acquired_cards: Set[str] = field(default_factory=set)
    width: int = 0
    height: int = 0
    events: list = field(default_factory=list)
