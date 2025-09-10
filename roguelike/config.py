from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml


@dataclass
class WindowConfig:
    width: int = 960
    height: int = 540
    title: str = "Roguelike Survivor"
    fps: int = 60


@dataclass
class GameplayConfig:
    player_move_speed: float = 180.0
    player_radius: int = 14
    player_color: tuple[int, int, int] = (60, 200, 255)
    player_max_health: int = 100
    player_regen_per_minute: int = 0

    enemy_base_speed: float = 80.0
    enemy_radius: int = 12
    enemy_color: tuple[int, int, int] = (240, 70, 70)
    enemy_damage: int = 10
    enemy_spawn_per_minute: int = 60
    enemy_spawn_distance_min: int = 250

    projectile_radius: int = 5
    projectile_color: tuple[int, int, int] = (255, 240, 120)

    pickup_radius: int = 6
    xp_color: tuple[int, int, int] = (140, 255, 140)


@dataclass
class SpawnConfig:
    enemy_spawn_interval: float = 1.0
    spawn_increase_every: float = 30.0
    spawn_increase_amount: float = 0.5


@dataclass
class MetaConfig:
    save_path: str = "save/profile.json"
    starting_currency: int = 0


@dataclass
class Settings:
    window: WindowConfig
    gameplay: GameplayConfig
    spawning: SpawnConfig
    meta: MetaConfig


def _tuple3(v: Any, default: tuple[int, int, int]) -> tuple[int, int, int]:
    try:
        a, b, c = v
        return int(a), int(b), int(c)
    except Exception:
        return default


def load_settings(path: str | Path = "config/settings.yaml") -> Settings:
    p = Path(path)
    raw: Dict[str, Any] = {}
    if p.exists():
        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}

    win = raw.get("window", {})
    window = WindowConfig(
        width=int(win.get("width", 960)),
        height=int(win.get("height", 540)),
        title=str(win.get("title", "Roguelike Survivor")),
        fps=int(win.get("fps", 60)),
    )

    gp = raw.get("gameplay", {})
    gameplay = GameplayConfig(
        player_move_speed=float(gp.get("player", {}).get("move_speed", 180.0)),
        player_radius=int(gp.get("player", {}).get("radius", 14)),
        player_color=_tuple3(gp.get("player", {}).get("color", (60, 200, 255)), (60, 200, 255)),
        player_max_health=int(gp.get("player", {}).get("max_health", 100)),
        player_regen_per_minute=int(gp.get("player", {}).get("regen_per_minute", 0)),
        enemy_base_speed=float(gp.get("enemy", {}).get("base_speed", 80.0)),
        enemy_radius=int(gp.get("enemy", {}).get("radius", 12)),
        enemy_color=_tuple3(gp.get("enemy", {}).get("color", (240, 70, 70)), (240, 70, 70)),
        enemy_damage=int(gp.get("enemy", {}).get("damage", 10)),
        enemy_spawn_per_minute=int(gp.get("enemy", {}).get("spawn_per_minute", 60)),
        enemy_spawn_distance_min=int(gp.get("enemy", {}).get("spawn_distance_min", 250)),
        projectile_radius=int(gp.get("projectile", {}).get("radius", 5)),
        projectile_color=_tuple3(gp.get("projectile", {}).get("color", (255, 240, 120)), (255, 240, 120)),
        pickup_radius=int(gp.get("pickup", {}).get("radius", 6)),
        xp_color=_tuple3(gp.get("pickup", {}).get("xp_color", (140, 255, 140)), (140, 255, 140)),
    )

    sp = raw.get("spawning", {})
    spawning = SpawnConfig(
        enemy_spawn_interval=float(sp.get("enemy_spawn_interval", 1.0)),
        spawn_increase_every=float(sp.get("spawn_increase_every", 30.0)),
        spawn_increase_amount=float(sp.get("spawn_increase_amount", 0.5)),
    )

    mt = raw.get("meta", {})
    meta = MetaConfig(
        save_path=str(mt.get("save_path", "save/profile.json")),
        starting_currency=int(mt.get("starting_currency", 0)),
    )

    return Settings(window=window, gameplay=gameplay, spawning=spawning, meta=meta)

