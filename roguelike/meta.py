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
    unlocked_mains: list[str] = None
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
            "unlocked_mains": self.unlocked_mains or [],
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
                    unlocked_mains=list(data.get("unlocked_mains", [])),
                    main_switch_unlocked=bool(data.get("main_switch_unlocked", False)),
                    selected_main=str(data.get("selected_main", "basic_bolt")),
                    achievements=dict(data.get("achievements", {})),
                    total_kills=int(data.get("total_kills", 0)),
                    total_time=float(data.get("total_time", 0.0)),
                    total_score=float(data.get("total_score", 0.0)),
                )
                # 迁移：确保基础武器与基础副武器已解锁
                if not self.profile.unlocked_mains:
                    self.profile.unlocked_mains = ['basic_bolt']
                if not self.profile.unlocked_subs:
                    self.profile.unlocked_subs = ['orbital_blade']
                # selected_main 必须属于已解锁
                if self.profile.selected_main not in self.profile.unlocked_mains:
                    self.profile.selected_main = self.profile.unlocked_mains[0]
                self.save()
            except Exception:
                self.profile = Profile(currency=starting_currency, unlocked_subs=['orbital_blade'], unlocked_mains=['basic_bolt'])
        else:
            self.profile = Profile(currency=starting_currency, unlocked_subs=['orbital_blade'], unlocked_mains=['basic_bolt'])
            self.save()
        self._loaded = True
        return self.profile

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.profile.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


class SaveManager:
    def __init__(self, base_dir: str = 'save', pattern: str = 'profile_slot{slot}.json') -> None:
        self.base = Path(base_dir)
        self.pattern = pattern

    def slot_path(self, slot: int) -> Path:
        return self.base / self.pattern.format(slot=slot)

    def list_slots(self, slots=(1, 2, 3)) -> dict:
        out = {}
        for s in slots:
            p = self.slot_path(s)
            out[s] = p.exists()
        return out

    def save_to_slot(self, slot: int, profile: Profile) -> None:
        p = self.slot_path(slot)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(profile.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')

    def load_from_slot(self, slot: int) -> Profile:
        p = self.slot_path(slot)
        prof = Profile()
        if p.exists():
            data = json.loads(p.read_text(encoding='utf-8'))
            prof = Profile(
                currency=int(data.get("currency", 0)),
                unlocks=dict(data.get("unlocks", {})),
                upgrades=dict(data.get("upgrades", {})),
                unlocked_subs=list(data.get("unlocked_subs", [])),
                unlocked_mains=list(data.get("unlocked_mains", [])),
                main_switch_unlocked=bool(data.get("main_switch_unlocked", False)),
                selected_main=str(data.get("selected_main", "basic_bolt")),
                achievements=dict(data.get("achievements", {})),
                total_kills=int(data.get("total_kills", 0)),
                total_time=float(data.get("total_time", 0.0)),
                total_score=float(data.get("total_score", 0.0)),
            )
        return prof

    def delete_slot(self, slot: int) -> None:
        p = self.slot_path(slot)
        if p.exists():
            p.unlink()
