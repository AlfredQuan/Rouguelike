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
class WorldConfig:
    width: int = 2400
    height: int = 2400
    grid_size: int = 64


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
    projectile_max_count: int = 500

    pickup_radius: int = 6
    xp_color: tuple[int, int, int] = (140, 255, 140)
    pickup_magnet_radius: float = 220.0
    pickup_max_count: int = 300


@dataclass
class SpawnConfig:
    enemy_spawn_interval: float = 1.0
    spawn_increase_every: float = 30.0
    spawn_increase_amount: float = 0.5
    offscreen_margin: int = 80


@dataclass
class MetaConfig:
    save_path: str = "save/profile.json"
    starting_currency: int = 0


@dataclass
class EconomyConfig:
    score_to_currency: float = 0.1
    kills_to_currency: float = 0.2
    time_to_currency: float = 0.0


@dataclass
class Settings:
    window: WindowConfig
    world: WorldConfig
    gameplay: GameplayConfig
    spawning: SpawnConfig
    meta: MetaConfig
    economy: EconomyConfig


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

    world_raw = raw.get("world", {})
    world = WorldConfig(
        width=int(world_raw.get("width", 2400)),
        height=int(world_raw.get("height", 2400)),
        grid_size=int(world_raw.get("grid_size", 64)),
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
        projectile_max_count=int(gp.get("projectile", {}).get("max_count", 500)),
        pickup_radius=int(gp.get("pickup", {}).get("radius", 6)),
        xp_color=_tuple3(gp.get("pickup", {}).get("xp_color", (140, 255, 140)), (140, 255, 140)),
        pickup_magnet_radius=float(gp.get("pickup", {}).get("magnet_radius", 220.0)),
        pickup_max_count=int(gp.get("pickup", {}).get("max_count", 300)),
    )

    sp = raw.get("spawning", {})
    spawning = SpawnConfig(
        enemy_spawn_interval=float(sp.get("enemy_spawn_interval", 1.0)),
        spawn_increase_every=float(sp.get("spawn_increase_every", 30.0)),
        spawn_increase_amount=float(sp.get("spawn_increase_amount", 0.5)),
        offscreen_margin=int(sp.get("offscreen_margin", 80)),
    )

    mt = raw.get("meta", {})
    meta = MetaConfig(
        save_path=str(mt.get("save_path", "save/profile.json")),
        starting_currency=int(mt.get("starting_currency", 0)),
    )

    eco_raw = raw.get("economy", {})
    economy = EconomyConfig(
        score_to_currency=float(eco_raw.get("score_to_currency", 0.1)),
        kills_to_currency=float(eco_raw.get("kills_to_currency", 0.2)),
        time_to_currency=float(eco_raw.get("time_to_currency", 0.0)),
    )

    return Settings(window=window, world=world, gameplay=gameplay, spawning=spawning, meta=meta, economy=economy)
