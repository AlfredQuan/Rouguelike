from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


def _load_yaml(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


class Content:
    def __init__(self, base_dir: str | Path = ".") -> None:
        self.base = Path(base_dir)
        self.characters = _load_yaml(self.base / "data/characters.yaml")
        self.enemies = _load_yaml(self.base / "data/enemies.yaml")
        # Support split weapon files; fallback to legacy weapons.yaml as main
        self.weapons_main = _load_yaml(self.base / "data/weapons_main.yaml")
        self.weapons_sub = _load_yaml(self.base / "data/weapons_sub.yaml")
        self.weapons_legacy = _load_yaml(self.base / "data/weapons.yaml")
        self.pickups = _load_yaml(self.base / "data/pickups.yaml")
        self.cards = _load_yaml(self.base / "data/cards.yaml")

    def character(self, key: str) -> Dict[str, Any]:
        return dict(self.characters.get(key, {}))

    def enemy(self, key: str) -> Dict[str, Any]:
        return dict(self.enemies.get(key, {}))

    def weapon(self, key: str) -> Dict[str, Any]:
        # legacy accessor: main weapons
        if self.weapons_main:
            return dict(self.weapons_main.get(key, {}))
        return dict(self.weapons_legacy.get(key, {}))

    def weapon_main(self, key: str) -> Dict[str, Any]:
        return dict((self.weapons_main or {}).get(key, {}))

    def weapon_sub(self, key: str) -> Dict[str, Any]:
        return dict((self.weapons_sub or {}).get(key, {}))
