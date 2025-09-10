from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict


@dataclass
class Position:
    x: float
    y: float


@dataclass
class Velocity:
    x: float = 0.0
    y: float = 0.0


@dataclass
class Sprite:
    color: tuple[int, int, int]
    radius: int


@dataclass
class Collider:
    radius: float


@dataclass
class Obstacle:
    solid: bool = True


@dataclass
class Health:
    current: int
    max_hp: int


@dataclass
class Faction:
    name: str  # 'player' or 'enemy'


@dataclass
class Player:
    pass


@dataclass
class Enemy:
    damage: int
    speed: float


@dataclass
class Projectile:
    damage: int
    lifetime: float
    speed: float
    dir_x: float
    dir_y: float
    owner: str  # 'player' or 'enemy'
    despawn_on_hit: bool = True
    pierce: int = 0  # how many enemies it can pierce before despawn; -1 = infinite


@dataclass
class Weapon:
    fire_rate: float
    cooldown: float
    damage: int
    proj_speed: float
    lifetime: float


@dataclass
class Pickup:
    kind: str  # 'xp' or 'heal'
    value: int


@dataclass
class Experience:
    xp: int = 0
    level: int = 1


@dataclass
class Speed:
    base: float
    mult: float = 1.0
    add: float = 0.0

    @property
    def value(self) -> float:
        return max(0.0, self.base * self.mult + self.add)


@dataclass
class WeaponInstance:
    key: str
    behavior: str
    fire_rate: float
    cooldown: float
    damage: int
    speed: float
    lifetime: float
    # Optional parameters per behavior
    count: int = 1
    spread_deg: float = 0.0
    radius: float = 100.0
    angular_speed_deg: float = 180.0
    state: Dict[str, object] = None  # for runtime data like spawned entity ids
    pierce: int = 0


@dataclass
class Loadout:
    main: Optional[WeaponInstance]
    sub: List[WeaponInstance]


@dataclass
class Orbit:
    owner: int
    radius: float
    angle_deg: float
    angular_speed_deg: float


@dataclass
class Field:
    owner: Optional[int]  # None for independent random fields; else follow owner
    radius: float
    dps: float
    lifetime: float  # -1 for infinite
    follow_owner: bool = False
    color: tuple[int, int, int] = (255, 120, 120)


@dataclass
class Hurtbox:
    cooldown: float = 0.0
    i_frames: float = 0.5  # seconds of invulnerability after a hit


@dataclass
class Shooter:
    range: float
    fire_rate: float
    cooldown: float
    proj_speed: float
    proj_damage: int
    proj_lifetime: float
    proj_color: tuple[int, int, int] = (255, 100, 100)
    proj_radius: int = 4
