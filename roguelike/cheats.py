from __future__ import annotations

import pygame
from .esper_compat import esper
from .context import GameContext
from .ecs_components import Experience, Health, Loadout, Player
from .factories import create_player
from .content import Content


class CheatSystem(esper.Processor):
    def __init__(self, ctx: GameContext, content: Content) -> None:
        super().__init__()
        self.ctx = ctx
        self.content = content

    def process(self, dt: float) -> None:
        # Non-blocking; read keydown events
        for event in getattr(self.ctx, 'events', []):
            if event.type != pygame.KEYDOWN:
                continue
            key = event.key
            if key == pygame.K_F1:
                # +10 XP
                for _, exp in self.world.get_component(Experience):
                    exp.xp += 10
                print("[Cheat] +10 XP")
            elif key == pygame.K_F2:
                # Heal to full
                for _, h in self.world.get_component(Health):
                    h.current = h.max_hp
                print("[Cheat] Heal to full")
            elif key == pygame.K_F3:
                # Unlock all sub weapons (meta)
                for k in (self.content.weapons_sub or {}).keys():
                    self.ctx.meta_unlocked_subs.add(k)
                # persist to profile via world attachment
                store = getattr(self.world, 'profile_store', None)
                profile = getattr(self.world, 'profile', None)
                if store and profile is not None:
                    cur = set(profile.unlocked_subs or [])
                    cur.update(self.ctx.meta_unlocked_subs)
                    profile.unlocked_subs = sorted(list(cur))
                    store.save()
                print("[Cheat] Unlocked all sub weapons (meta)")
            elif key == pygame.K_F4:
                # Give a sub weapon (orbital blade)
                self._add_sub("orbital_blade")
            elif key == pygame.K_F5:
                # Give sniper as main (adds alongside)
                self._add_main("sniper")
            elif key == pygame.K_F7:
                # Add tri_shot main
                self._add_main("tri_shot")
            elif key == pygame.K_F8:
                # Add nova_burst main
                self._add_main("nova_burst")
            elif key == pygame.K_F9:
                # Add rapid_blaster main
                self._add_main("rapid_blaster")
            elif key == pygame.K_F10:
                # Clear all main weapons (to isolate testing)
                self._clear_mains()
            elif key == pygame.K_F11:
                # Add Garlic Aura
                self._add_sub("aura_garlic")
            elif key == pygame.K_F12:
                # Add Random Storm
                self._add_sub("random_storm")
            elif key == pygame.K_F6:
                # Force open card selection (random 3 available)
                # Build available from cards and context using LevelUpSystem's availability logic
                from .ecs_systems import LevelUpSystem as _L  # noqa
                cards = self.content.cards
                # Use a temporary LevelUpSystem instance to reuse availability logic
                lus = _L(self.ctx, cards)
                lus.world = self.world
                avail = [k for k, v in cards.items() if lus._is_available(k, v)]
                if avail:
                    self.ctx.levelup_choices = [self.ctx.rng.choice(avail) for _ in range(3)]
                    self.ctx.paused = True
                print("[Cheat] Opened card selection")

    def _player_loadout(self):
        for e, (ld,) in self.world.get_components(Loadout):
            return e, ld
        return None, None

    def _add_sub(self, key: str) -> None:
        pe, ld = self._player_loadout()
        if pe is None or ld is None:
            return
        wd = self.content.weapon_sub(key)
        if not wd:
            return
        from .ecs_components import WeaponInstance
        inst = WeaponInstance(
            key=key,
            behavior=str(wd.get("behavior", "orbital")),
            fire_rate=float(wd.get("fire_rate", 1.0)),
            cooldown=0.0,
            damage=int(wd.get("damage", 5)),
            speed=float(wd.get("speed", 0.0)),
            lifetime=float(wd.get("lifetime", -1.0)),
            count=int(wd.get("count", 1)),
            spread_deg=float(wd.get("spread_deg", 0.0)),
            radius=float(wd.get("radius", 100.0)),
            angular_speed_deg=float(wd.get("angular_speed_deg", 180.0)),
            state={},
        )
        ld.sub.append(inst)
        print(f"[Cheat] Added sub weapon: {key}")

    def _add_main(self, key: str) -> None:
        pe, ld = self._player_loadout()
        if pe is None or ld is None:
            return
        wd = self.content.weapon_main(key) or self.content.weapon(key)
        if not wd:
            return
        from .ecs_components import WeaponInstance
        inst = WeaponInstance(
            key=key,
            behavior=str(wd.get("behavior", "projectile")),
            fire_rate=float(wd.get("fire_rate", 2.0)),
            cooldown=0.0,
            damage=int(wd.get("damage", 10)),
            speed=float(wd.get("speed", 350.0)),
            lifetime=float(wd.get("lifetime", 1.2)),
            count=int(wd.get("count", 1)),
            spread_deg=float(wd.get("spread_deg", 0.0)),
            state={},
        )
        ld.main = inst
        print(f"[Cheat] Set main weapon: {key}")

    def _clear_mains(self) -> None:
        pe, ld = self._player_loadout()
        if pe is None or ld is None:
            return
        ld.main = None
        print("[Cheat] Cleared main weapon")
