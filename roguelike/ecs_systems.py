from __future__ import annotations

import math
import random
from typing import Optional

from .esper_compat import esper
import pygame

from .ecs_components import (
    Collider,
    Enemy,
    Experience,
    Faction,
    Health,
    Loadout,
    Orbit,
    Pickup,
    Player,
    Position,
    Projectile,
    Sprite,
    Speed,
    Velocity,
    WeaponInstance,
)
from .context import GameContext


def _norm(x: float, y: float) -> tuple[float, float, float]:
    mag = math.hypot(x, y)
    if mag == 0:
        return 0.0, 0.0, 0.0
    return x / mag, y / mag, mag


class InputSystem(esper.Processor):
    def __init__(self, ctx: GameContext) -> None:
        super().__init__()
        self.ctx = ctx

    def process(self, dt: float) -> None:
        if self.ctx.paused:
            return
        keys = pygame.key.get_pressed()
        dx = dy = 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += 1
        ndx, ndy, _ = _norm(dx, dy)
        for _, (p, v, _pl, spd) in self.world.get_components(Position, Velocity, Player, Speed):
            v.x = ndx * spd.value
            v.y = ndy * spd.value


class MovementSystem(esper.Processor):
    def __init__(self, ctx: GameContext) -> None:
        super().__init__()
        self.ctx = ctx

    def process(self, dt: float) -> None:
        if self.ctx.paused:
            return
        for _, (p, v) in self.world.get_components(Position, Velocity):
            p.x += v.x * dt
            p.y += v.y * dt


class EnemyAISystem(esper.Processor):
    def __init__(self, ctx: GameContext, speed_scale: float = 1.0) -> None:
        super().__init__()
        self.ctx = ctx
        self.speed_scale = speed_scale

    def process(self, dt: float) -> None:
        if self.ctx.paused:
            return
        player_pos: Optional[Position] = None
        for _, (p, _pl) in self.world.get_components(Position, Player):
            player_pos = p
            break
        if player_pos is None:
            return
        px, py = player_pos.x, player_pos.y
        for _, (pos, vel, enemy) in self.world.get_components(Position, Velocity, Enemy):
            dx, dy = px - pos.x, py - pos.y
            ndx, ndy, _ = _norm(dx, dy)
            vel.x = ndx * enemy.speed * self.speed_scale
            vel.y = ndy * enemy.speed * self.speed_scale


class CollisionSystem(esper.Processor):
    def __init__(self, ctx: GameContext, width: int, height: int) -> None:
        super().__init__()
        self.ctx = ctx
        self.width = width
        self.height = height

    def process(self, dt: float) -> None:
        if self.ctx.paused:
            return
        # Projectile vs enemies
        for pe, (ppos, pcol, proj) in self.world.get_components(Position, Collider, Projectile):
            if proj.owner != "player":
                continue
            for ee, (epos, ecol, _enemy, ehealth) in self.world.get_components(
                Position, Collider, Enemy, Health
            ):
                if (ppos.x - epos.x) ** 2 + (ppos.y - epos.y) ** 2 <= (pcol.radius + ecol.radius) ** 2:
                    ehealth.current -= proj.damage
                    if proj.despawn_on_hit:
                        self.world.delete_entity(pe)
                    break

        # Enemy vs player
        for pe, (ppos, pcol, _pl, phealth) in self.world.get_components(Position, Collider, Player, Health):
            for ee, (epos, ecol, enemy) in self.world.get_components(Position, Collider, Enemy):
                if (ppos.x - epos.x) ** 2 + (ppos.y - epos.y) ** 2 <= (pcol.radius + ecol.radius) ** 2:
                    phealth.current -= enemy.damage

        # Player vs pickups
        for pe, (ppos, pcol, _pl, phealth, pexp) in self.world.get_components(
            Position, Collider, Player, Health, Experience
        ):
            for xe, (xpos, xcol, pick) in self.world.get_components(Position, Collider, Pickup):
                if (ppos.x - xpos.x) ** 2 + (ppos.y - xpos.y) ** 2 <= (pcol.radius + xcol.radius) ** 2:
                    if pick.kind == "xp":
                        pexp.xp += pick.value
                    elif pick.kind == "heal":
                        phealth.current = min(phealth.max_hp, phealth.current + pick.value)
                    self.world.delete_entity(xe)


class RenderSystem(esper.Processor):
    def __init__(self, ctx: GameContext, cards: dict[str, dict], surface: pygame.Surface, width: int, height: int) -> None:
        super().__init__()
        self.ctx = ctx
        self.cards = cards
        self.surf = surface
        self.width = width
        self.height = height

    def process(self, dt: float) -> None:
        self.surf.fill((20, 20, 24))
        for _, (pos, sprite) in self.world.get_components(Position, Sprite):
            pygame.draw.circle(self.surf, sprite.color, (int(pos.x), int(pos.y)), sprite.radius)

        # HUD: health bar, xp bar, level
        font = pygame.font.Font(None, 22)
        # Player stats
        for _, (h, exp) in self.world.get_components(Health, Experience):
            # HP bar
            hp_ratio = max(0.0, min(1.0, h.current / max(1, h.max_hp)))
            pygame.draw.rect(self.surf, (60, 60, 60), pygame.Rect(20, 20, 200, 12))
            pygame.draw.rect(self.surf, (60, 200, 80), pygame.Rect(20, 20, int(200 * hp_ratio), 12))
            self.surf.blit(font.render(f"HP {h.current}/{h.max_hp}", True, (230, 230, 230)), (230, 18))
            # XP bar (uses simple threshold function for preview)
            xp_need = 5 + (exp.level - 1) * 2
            xp_ratio = max(0.0, min(1.0, exp.xp / max(1, xp_need)))
            pygame.draw.rect(self.surf, (60, 60, 60), pygame.Rect(20, 40, 200, 10))
            pygame.draw.rect(self.surf, (120, 180, 255), pygame.Rect(20, 40, int(200 * xp_ratio), 10))
            self.surf.blit(font.render(f"Lv {exp.level}", True, (230, 230, 230)), (230, 38))

        # Weapon HUD: show counts/types for quick feedback
        x0, y0 = 20, 60
        small = pygame.font.Font(None, 20)
        for _, (loadout,) in self.world.get_components(Loadout):
            mains = ", ".join([w.key for w in loadout.main]) or "-"
            subs = ", ".join([w.key for w in loadout.sub]) or "-"
            self.surf.blit(small.render(f"Main: {mains}", True, (230, 230, 230)), (x0, y0))
            self.surf.blit(small.render(f"Sub:  {subs}", True, (230, 230, 230)), (x0, y0 + 18))

        # Level-up overlay
        if self.ctx.paused and self.ctx.levelup_choices:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            self.surf.blit(overlay, (0, 0))
            big_font = pygame.font.Font(None, 36)
            self.surf.blit(big_font.render("Choose an Upgrade (1/2/3)", True, (255, 255, 255)), (self.width//2 - 180, 120))
            # Cards layout
            cw, ch = 220, 120
            spacing = 40
            total_w = 3 * cw + 2 * spacing
            start_x = self.width // 2 - total_w // 2
            y = 180
            for i, key in enumerate(self.ctx.levelup_choices):
                x = start_x + i * (cw + spacing)
                pygame.draw.rect(self.surf, (50, 50, 60), pygame.Rect(x, y, cw, ch), border_radius=8)
                pygame.draw.rect(self.surf, (200, 200, 220), pygame.Rect(x, y, cw, ch), 2, border_radius=8)
                self.surf.blit(big_font.render(f"{i+1}", True, (255, 255, 255)), (x + cw - 30, y + 8))
                card = self.cards.get(key, {})
                name = str(card.get("name", key))
                desc = str(card.get("description", ""))
                title_font = pygame.font.Font(None, 28)
                small_font = pygame.font.Font(None, 22)
                self.surf.blit(title_font.render(name, True, (255, 255, 255)), (x + 12, y + 16))
                # Wrap desc roughly
                words = desc.split()
                line = ""
                yy = y + 48
                for w in words:
                    if small_font.size(line + (" " if line else "") + w)[0] > cw - 24:
                        self.surf.blit(small_font.render(line, True, (220, 220, 230)), (x + 12, yy))
                        yy += 22
                        line = w
                    else:
                        line = (line + " " + w).strip()
                if line:
                    self.surf.blit(small_font.render(line, True, (220, 220, 230)), (x + 12, yy))


class WeaponFireSystem(esper.Processor):
    def __init__(self, ctx: GameContext) -> None:
        super().__init__()
        self.ctx = ctx

    def process(self, dt: float) -> None:
        if self.ctx.paused:
            return
        for pe, (ppos, _pl, loadout) in self.world.get_components(Position, Player, Loadout):
            # Main weapons: projectile-like behaviors
            for w in loadout.main:
                w.cooldown -= dt
                if w.cooldown <= 0:
                    self._fire_main(ppos, w)
                    w.cooldown = 1.0 / max(0.01, w.fire_rate)
            # Sub weapons: some are persistent (orbital), some burst
            for w in loadout.sub:
                if w.behavior == "orbital":
                    self._ensure_orbitals(pe, ppos, w)
                else:
                    w.cooldown -= dt
                    if w.cooldown <= 0:
                        self._fire_sub(ppos, w)
                        w.cooldown = 1.0 / max(0.01, w.fire_rate)

    def _nearest_enemy(self, ppos: Position) -> Optional[tuple[float, float]]:
        best_d2 = 1e18
        best: Optional[tuple[float, float]] = None
        for _, (epos, _enemy) in self.world.get_components(Position, Enemy):
            d2 = (epos.x - ppos.x) ** 2 + (epos.y - ppos.y) ** 2
            if d2 < best_d2:
                best_d2 = d2
                best = (epos.x, epos.y)
        return best

    def _spawn_projectile(self, x: float, y: float, dx: float, dy: float, damage: int, lifetime: float, speed: float, color=(255, 240, 120), radius=5, despawn_on_hit=True) -> None:
        proj = self.world.create_entity()
        self.world.add_component(proj, Position(x, y))
        self.world.add_component(proj, Velocity(dx * speed, dy * speed))
        self.world.add_component(proj, Projectile(damage, lifetime, speed, dx, dy, owner="player", despawn_on_hit=despawn_on_hit))
        self.world.add_component(proj, Collider(radius=radius))
        self.world.add_component(proj, Sprite(color, radius))

    def _fire_main(self, ppos: Position, w: WeaponInstance) -> None:
        target = self._nearest_enemy(ppos)
        if target is not None:
            tx, ty = target
            dx, dy = tx - ppos.x, ty - ppos.y
            ndx, ndy, _ = _norm(dx, dy)
        else:
            ndx, ndy = 1.0, 0.0

        if w.behavior == "projectile":
            # count + spread
            cx, cy = ppos.x, ppos.y
            if w.count <= 1 or w.spread_deg == 0:
                self._spawn_projectile(cx, cy, ndx, ndy, w.damage, w.lifetime, w.speed)
            else:
                # build spread around direction
                angle0 = math.degrees(math.atan2(ndy, ndx))
                if w.count == 1:
                    angles = [angle0]
                else:
                    total = w.spread_deg
                    step = total / (w.count - 1)
                    start = angle0 - total / 2
                    angles = [start + i * step for i in range(w.count)]
                for a in angles:
                    rad = math.radians(a)
                    vx, vy = math.cos(rad), math.sin(rad)
                    self._spawn_projectile(cx, cy, vx, vy, w.damage, w.lifetime, w.speed)
        elif w.behavior == "radial_burst":
            cx, cy = ppos.x, ppos.y
            cnt = max(1, w.count)
            for i in range(cnt):
                a = (i / cnt) * 2 * math.pi
                vx, vy = math.cos(a), math.sin(a)
                self._spawn_projectile(cx, cy, vx, vy, w.damage, w.lifetime, w.speed)
        else:
            # default projectile
            self._spawn_projectile(ppos.x, ppos.y, ndx, ndy, w.damage, w.lifetime, w.speed)

    def _fire_sub(self, ppos: Position, w: WeaponInstance) -> None:
        if w.behavior == "radial_burst":
            cx, cy = ppos.x, ppos.y
            cnt = max(1, w.count)
            for i in range(cnt):
                a = (i / cnt) * 2 * math.pi
                vx, vy = math.cos(a), math.sin(a)
                self._spawn_projectile(cx, cy, vx, vy, w.damage, w.lifetime, w.speed, color=(200, 255, 200))

    def _ensure_orbitals(self, owner_eid: int, ppos: Position, w: WeaponInstance) -> None:
        if w.state is None:
            w.state = {}
        spawned: list[int] = list(w.state.get("entities", []))
        need = max(1, w.count)
        # Spawn missing
        while len(spawned) < need:
            idx = len(spawned)
            angle = (idx / need) * 360.0
            e = self.world.create_entity()
            self.world.add_component(e, Position(ppos.x, ppos.y))
            self.world.add_component(e, Velocity(0, 0))
            self.world.add_component(e, Orbit(owner=owner_eid, radius=w.radius, angle_deg=angle, angular_speed_deg=w.angular_speed_deg))
            self.world.add_component(e, Collider(radius=6))
            self.world.add_component(e, Projectile(w.damage, -1.0, 0.0, 0.0, 0.0, owner="player", despawn_on_hit=False))
            self.world.add_component(e, Sprite((200, 220, 255), 6))
            spawned.append(e)
        w.state["entities"] = spawned


class ProjectileLifetimeSystem(esper.Processor):
    def __init__(self, ctx: GameContext) -> None:
        super().__init__()
        self.ctx = ctx

    def process(self, dt: float) -> None:
        if self.ctx.paused:
            return
        to_delete = []
        for e, proj in self.world.get_component(Projectile):
            if proj.lifetime >= 0:
                proj.lifetime -= dt
            if proj.lifetime >= 0 and proj.lifetime <= 0:
                to_delete.append(e)
        for e in to_delete:
            self.world.delete_entity(e)


class EnemyDeathSystem(esper.Processor):
    def __init__(self, ctx: GameContext, rng: random.Random) -> None:
        super().__init__()
        self.ctx = ctx
        self.rng = rng

    def process(self, dt: float) -> None:
        if self.ctx.paused:
            return
        to_delete = []
        for e, (pos, health, _enemy) in self.world.get_components(Position, Health, Enemy):
            if health.current <= 0:
                to_delete.append((e, pos))
        for e, pos in to_delete:
            # Drop XP gem with some chance
            if self.rng.random() < 0.9:
                xe = self.world.create_entity()
                self.world.add_component(xe, Position(pos.x, pos.y))
                self.world.add_component(xe, Collider(6))
                self.world.add_component(xe, Pickup("xp", 1))
                self.world.add_component(xe, Sprite((140, 255, 140), 6))
            self.world.delete_entity(e)


class EnemySpawnSystem(esper.Processor):
    def __init__(self, ctx: GameContext, width: int, height: int, base_interval: float, min_distance: float, enemy_speed: float, enemy_damage: int, enemy_color: tuple[int, int, int]) -> None:
        super().__init__()
        self.ctx = ctx
        self.width = width
        self.height = height
        self.interval = base_interval
        self.timer = 0.0
        self.min_distance = min_distance
        self.enemy_speed = enemy_speed
        self.enemy_damage = enemy_damage
        self.enemy_color = enemy_color
        self.rng = random.Random(42)

    def process(self, dt: float) -> None:
        if self.ctx.paused:
            return
        self.timer += dt
        if self.timer >= self.interval:
            self.timer -= self.interval
            self._spawn_enemy()

    def _spawn_enemy(self) -> None:
        player_pos: Optional[Position] = None
        for _, (ppos, _pl) in self.world.get_components(Position, Player):
            player_pos = ppos
            break
        if player_pos is None:
            return
        # Spawn around edges at least min_distance away
        for _ in range(20):
            side = self.rng.choice(["top", "bottom", "left", "right"])
            if side == "top":
                x = self.rng.uniform(0, self.width)
                y = -20
            elif side == "bottom":
                x = self.rng.uniform(0, self.width)
                y = self.height + 20
            elif side == "left":
                x = -20
                y = self.rng.uniform(0, self.height)
            else:
                x = self.width + 20
                y = self.rng.uniform(0, self.height)
            dx, dy = x - player_pos.x, y - player_pos.y
            _, _, dist = _norm(dx, dy)
            if dist >= self.min_distance:
                e = self.world.create_entity()
                self.world.add_component(e, Position(x, y))
                self.world.add_component(e, Velocity(0, 0))
                self.world.add_component(e, Enemy(damage=self.enemy_damage, speed=self.enemy_speed))
                self.world.add_component(e, Health(current=20, max_hp=20))
                self.world.add_component(e, Collider(radius=12))
                self.world.add_component(e, Faction("enemy"))
                self.world.add_component(e, Sprite(self.enemy_color, 12))
                break


class OrbitSystem(esper.Processor):
    def __init__(self, ctx: GameContext) -> None:
        super().__init__()
        self.ctx = ctx

    def process(self, dt: float) -> None:
        if self.ctx.paused:
            return
        for e, (pos, orb) in self.world.get_components(Position, Orbit):
            owner_pos = self.world.component_for_entity(orb.owner, Position)
            if owner_pos is None:
                continue
            # advance angle
            orb.angle_deg = (orb.angle_deg + orb.angular_speed_deg * dt) % 360.0
            rad = math.radians(orb.angle_deg)
            pos.x = owner_pos.x + math.cos(rad) * orb.radius
            pos.y = owner_pos.y + math.sin(rad) * orb.radius


def xp_needed_for_level(level: int) -> int:
    return 5 + (level - 1) * 2


class LevelUpSystem(esper.Processor):
    def __init__(self, ctx: GameContext, cards: dict[str, dict]) -> None:
        super().__init__()
        self.ctx = ctx
        self.cards = cards

    def process(self, dt: float) -> None:
        # If already paused for selection, do nothing here
        if self.ctx.paused:
            return
        for pe, exp in self.world.get_component(Experience):
            need = xp_needed_for_level(exp.level)
            if exp.xp >= need:
                exp.xp -= need
                exp.level += 1
                # Offer 3 random cards
                keys = list(self.cards.keys())
                if not keys:
                    return
                self.ctx.levelup_choices = [self.ctx.rng.choice(keys) for _ in range(3)]
                self.ctx.paused = True
                break


def apply_card_effect(world: esper.World, player_eid: int, effect: str, amount: float) -> None:
    if effect == "player_move_speed_mul":
        spd = world.component_for_entity(player_eid, Speed)
        spd.mult *= float(amount)
    elif effect == "player_max_health_add":
        h = world.component_for_entity(player_eid, Health)
        h.max_hp += int(amount)
        h.current = min(h.max_hp, h.current + int(amount))


class MenuInputSystem(esper.Processor):
    def __init__(self, ctx: GameContext, cards: dict[str, dict]) -> None:
        super().__init__()
        self.ctx = ctx
        self.cards = cards

    def process(self, dt: float) -> None:
        if not (self.ctx.paused and self.ctx.levelup_choices):
            return
        for event in pygame.event.get([pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN]):
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_1, pygame.K_KP1):
                    idx = 0
                elif event.key in (pygame.K_2, pygame.K_KP2):
                    idx = 1
                elif event.key in (pygame.K_3, pygame.K_KP3):
                    idx = 2
                else:
                    continue
                self._choose(idx)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                idx = self._hit_test(event.pos)
                if idx is not None:
                    self._choose(idx)

    def _choose(self, idx: int) -> None:
        if not self.ctx.levelup_choices:
            return
        idx = max(0, min(idx, len(self.ctx.levelup_choices) - 1))
        key = self.ctx.levelup_choices[idx]
        # find player
        player_eid = None
        for e, _ in self.world.get_component(Player):
            player_eid = e
            break
        if player_eid is None:
            return
        card = self.cards.get(key, {})
        effect = card.get("effect")
        amount = float(card.get("amount", 0))
        if effect:
            apply_card_effect(self.world, player_eid, effect, amount)
        # Unpause
        self.ctx.paused = False
        self.ctx.levelup_choices = None

    def _hit_test(self, pos: tuple[int, int]) -> Optional[int]:
        w, h = pygame.display.get_surface().get_size()
        cw, ch = 220, 120
        spacing = 40
        total_w = 3 * cw + 2 * spacing
        start_x = w // 2 - total_w // 2
        y = 180
        x0, y0 = pos
        for i in range(3):
            x = start_x + i * (cw + spacing)
            rect = pygame.Rect(x, y, cw, ch)
            if rect.collidepoint(x0, y0):
                return i
        return None
