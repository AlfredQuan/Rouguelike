from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Set
import random
from typing import Any


@dataclass
class RunStats:
    time_sec: float = 0.0
    kills: int = 0
    score: float = 0.0
    earned_currency: int = 0


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
    stats: RunStats = field(default_factory=RunStats)
    # Camera world position (follows player)
    cam_x: float = 0.0
    cam_y: float = 0.0
    world_width: int = 2400
    world_height: int = 2400
    grid_size: int = 64
