from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import load_settings
from .content import Content
from .meta import ProfileStore


app = FastAPI(title="Roguelike Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UnlockRequest(BaseModel):
    key: str


class SelectMainRequest(BaseModel):
    key: str


class CheatCurrencyRequest(BaseModel):
    amount: int = 10


def _store():
    settings = load_settings()
    return settings, ProfileStore(settings.meta.save_path)


@app.get("/api/settings")
def get_settings() -> Dict[str, Any]:
    s = load_settings()
    return {
        "window": s.window.__dict__,
        "world": s.world.__dict__,
        "gameplay": s.gameplay.__dict__,
        "spawning": s.spawning.__dict__,
        "economy": s.economy.__dict__,
    }


@app.get("/api/content/{kind}")
def get_content(kind: str) -> Dict[str, Any]:
    c = Content()
    if kind == "characters":
        return c.characters
    if kind == "enemies":
        return c.enemies
    if kind == "weapons_main":
        return c.weapons_main or c.weapons_legacy
    if kind == "weapons_sub":
        return c.weapons_sub
    if kind == "cards":
        return c.cards
    if kind == "achievements":
        return c.achievements
    raise HTTPException(404, f"Unknown content kind: {kind}")


@app.get("/api/profile")
def get_profile() -> Dict[str, Any]:
    settings, store = _store()
    p = store.load(settings.meta.starting_currency)
    return p.to_dict()


@app.post("/api/profile/unlock_sub")
def unlock_sub(req: UnlockRequest) -> Dict[str, Any]:
    settings, store = _store()
    p = store.load(settings.meta.starting_currency)
    us = set(p.unlocked_subs or [])
    us.add(req.key)
    p.unlocked_subs = sorted(list(us))
    store.save()
    return p.to_dict()


@app.post("/api/profile/select_main")
def select_main(req: SelectMainRequest) -> Dict[str, Any]:
    settings, store = _store()
    p = store.load(settings.meta.starting_currency)
    p.selected_main = req.key
    store.save()
    return p.to_dict()


@app.post("/api/profile/reset")
def reset_profile() -> Dict[str, Any]:
    settings, store = _store()
    p = store.load(settings.meta.starting_currency)
    p.currency = 0
    p.unlocked_subs = []
    p.main_switch_unlocked = False
    p.selected_main = "basic_bolt"
    p.achievements = {}
    p.total_kills = 0
    p.total_time = 0.0
    p.total_score = 0.0
    store.save()
    return p.to_dict()


@app.post("/api/cheat/currency")
def cheat_currency(req: CheatCurrencyRequest) -> Dict[str, Any]:
    settings, store = _store()
    p = store.load(settings.meta.starting_currency)
    p.currency += int(req.amount)
    store.save()
    return p.to_dict()


# Placeholder endpoints for future run integration
@app.post("/api/run/start")
def run_start() -> Dict[str, Any]:
    return {"status": "ok"}


@app.post("/api/run/end")
def run_end(payload: Dict[str, Any]) -> Dict[str, Any]:
    # payload can include stats to award currency server-side
    return {"status": "ok"}

