from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Profile:
    currency: int = 0
    unlocks: dict[str, bool] = None
    upgrades: dict[str, int] = None
    unlocked_subs: list[str] = None
    main_switch_unlocked: bool = False
    selected_main: str = "basic_bolt"
    achievements: dict[str, bool] = None
    total_kills: int = 0
    total_time: float = 0.0
    total_score: float = 0.0

    def to_dict(self):
        return {
            "currency": self.currency,
            "unlocks": self.unlocks or {},
            "upgrades": self.upgrades or {},
            "unlocked_subs": self.unlocked_subs or [],
            "main_switch_unlocked": self.main_switch_unlocked,
            "selected_main": self.selected_main,
            "achievements": self.achievements or {},
            "total_kills": self.total_kills,
            "total_time": self.total_time,
            "total_score": self.total_score,
        }


class ProfileStore:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.profile = Profile()
        self._loaded = False

    def load(self, starting_currency: int = 0) -> Profile:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self.profile = Profile(
                    currency=int(data.get("currency", starting_currency)),
                    unlocks=dict(data.get("unlocks", {})),
                    upgrades=dict(data.get("upgrades", {})),
                    unlocked_subs=list(data.get("unlocked_subs", [])),
                    main_switch_unlocked=bool(data.get("main_switch_unlocked", False)),
                    selected_main=str(data.get("selected_main", "basic_bolt")),
                    achievements=dict(data.get("achievements", {})),
                    total_kills=int(data.get("total_kills", 0)),
                    total_time=float(data.get("total_time", 0.0)),
                    total_score=float(data.get("total_score", 0.0)),
                )
            except Exception:
                self.profile = Profile(currency=starting_currency, unlocked_subs=[])
        else:
            self.profile = Profile(currency=starting_currency, unlocked_subs=[])
            self.save()
        self._loaded = True
        return self.profile

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.profile.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
