from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Profile:
    currency: int = 0
    unlocks: dict[str, bool] = None
    upgrades: dict[str, int] = None

    def to_dict(self):
        return {
            "currency": self.currency,
            "unlocks": self.unlocks or {},
            "upgrades": self.upgrades or {},
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
                )
            except Exception:
                self.profile = Profile(currency=starting_currency)
        else:
            self.profile = Profile(currency=starting_currency)
            self.save()
        self._loaded = True
        return self.profile

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.profile.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

