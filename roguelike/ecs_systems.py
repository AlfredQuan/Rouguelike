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
    Obstacle,
    Loadout,
    Orbit,
    Field,
    Pickup,
    Player,
    Position,
    Projectile,
    Sprite,
    Speed,
    Velocity,
    WeaponInstance,
    Hurtbox,
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
        # Move all entities with velocity
        for e, (p, v) in self.world.get_components(Position, Velocity):
            oldx, oldy = p.x, p.y
            p.x += v.x * dt
            p.y += v.y * dt
            # Clamp to world bounds for player and enemies
            if self.world.component_for_entity(e, Player) is not None or self.world.component_for_entity(e, Enemy) is not None:
                p.x = max(0, min(self.ctx.world_width, p.x))
                p.y = max(0, min(self.ctx.world_height, p.y))
            # Resolve collisions with obstacles for player
            if self.world.component_for_entity(e, Player) is not None:
                for _, (op, ocol, _obs) in self.world.get_components(Position, Collider, Obstacle):
                    dx, dy = p.x - op.x, p.y - op.y
                    dist2 = dx*dx + dy*dy
                    min_dist = ocol.radius + self.world.component_for_entity(e, Collider).radius
                    if dist2 < min_dist * min_dist:
                        ndx, ndy, dist = _norm(dx, dy)
                        push = min_dist - dist
                        p.x += ndx * push
                        p.y += ndy * push


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
                        if proj.pierce == 0:
                            self.world.delete_entity(pe)
                            break
                        elif proj.pierce > 0:
                            proj.pierce -= 1
                    break

        # Enemy vs player (with invulnerability frames)
        for pe, (ppos, pcol, _pl, phealth, phurt) in self.world.get_components(Position, Collider, Player, Health, Hurtbox):
            for ee, (epos, ecol, enemy) in self.world.get_components(Position, Collider, Enemy):
                if (ppos.x - epos.x) ** 2 + (ppos.y - epos.y) ** 2 <= (pcol.radius + ecol.radius) ** 2:
                    if phurt.cooldown <= 0.0:
                        phealth.current -= enemy.damage
                        phurt.cooldown = phurt.i_frames
                        break

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
    def __init__(self, ctx: GameContext, cards: dict[str, dict], surface: pygame.Surface, width: int, height: int, grid_size: int) -> None:
        super().__init__()
        self.ctx = ctx
        self.cards = cards
        self.surf = surface
        self.width = width
        self.height = height
        self.grid_size = grid_size

    def process(self, dt: float) -> None:
        # Camera offset
        camx, camy = self.ctx.cam_x, self.ctx.cam_y
        ox = int(self.width // 2 - camx)
        oy = int(self.height // 2 - camy)

        # Background grid
        self.surf.fill((16, 16, 20))
        gs = max(8, self.grid_size)
        color_grid = (30, 30, 36)
        start_x = (camx // gs) * gs - self.width
        start_y = (camy // gs) * gs - self.height
        x = start_x
        while x < camx + self.width:
            sx = int(x + ox)
            pygame.draw.line(self.surf, color_grid, (sx, 0), (sx, self.height))
            x += gs
        y = start_y
        while y < camy + self.height:
            sy = int(y + oy)
            pygame.draw.line(self.surf, color_grid, (0, sy), (self.width, sy))
            y += gs

        # World bounds rectangle
        wb = pygame.Rect(ox, oy, self.ctx.world_width, self.ctx.world_height)
        pygame.draw.rect(self.surf, (60, 60, 72), wb, 2)

        # Entities
        for _, (pos, sprite) in self.world.get_components(Position, Sprite):
            pygame.draw.circle(self.surf, sprite.color, (int(pos.x + ox), int(pos.y + oy)), sprite.radius)

        # Draw AoE fields as translucent circles
        for _, (pos, fld) in self.world.get_components(Position, Field):
            r = int(fld.radius)
            if r <= 0:
                continue
            overlay = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            color = (*fld.color[:3], 60)
            pygame.draw.circle(overlay, color, (r + 2, r + 2), r)
            self.surf.blit(overlay, (int(pos.x + ox - r - 2), int(pos.y + oy - r - 2)))

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
            # Score line moved lower to avoid overlap
            self.surf.blit(font.render(f"Time {self.ctx.stats.time_sec:.0f}s  Score {int(self.ctx.stats.score)}  Kills {self.ctx.stats.kills}", True, (230, 230, 230)), (20, 64))

        # Weapon HUD: show counts/types for quick feedback
        x0, y0 = 20, 60
        small = pygame.font.Font(None, 20)
        for _, (loadout,) in self.world.get_components(Loadout):
            main_key = loadout.main.key if loadout.main is not None else "-"
            subs = ", ".join([w.key for w in loadout.sub]) or "-"
            self.surf.blit(small.render(f"Main: {main_key}", True, (230, 230, 230)), (x0, y0))
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
        elif self.ctx.paused:
            # Pause menu with cheat help
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            self.surf.blit(overlay, (0, 0))
            big = pygame.font.Font(None, 36)
            self.surf.blit(big.render("Paused", True, (255, 255, 255)), (self.width//2 - 60, 110))
            info = [
                "Cheats:",
                "F1 +10 XP, F2 Heal, F3 Unlock all subs",
                "F4 Add orbital, F11 Aura, F12 Storm",
                "F5 Sniper, F7 Tri, F8 Nova, F9 Rapid, F10 Clear main, C +10 Currency",
                "Press P to resume",
            ]
            y = 160
            for line in info:
                self.surf.blit(font.render(line, True, (230, 230, 230)), (self.width//2 - 260, y))
                y += 24


class WeaponFireSystem(esper.Processor):
    def __init__(self, ctx: GameContext) -> None:
        super().__init__()
        self.ctx = ctx

    def process(self, dt: float) -> None:
        if self.ctx.paused:
            return
        for pe, (ppos, _pl, loadout) in self.world.get_components(Position, Player, Loadout):
            # Main weapons: projectile-like behaviors
            if loadout.main is not None:
                w = loadout.main
                w.cooldown -= dt
                if w.cooldown <= 0:
                    self._fire_main(ppos, w)
                    w.cooldown = 1.0 / max(0.01, w.fire_rate)
            # Sub weapons: some are persistent (orbital), some burst
            for w in loadout.sub:
                if w.behavior == "orbital":
                    self._ensure_orbitals(pe, ppos, w)
                elif w.behavior == "aura":
                    self._ensure_aura(pe, ppos, w)
                elif w.behavior == "random_field":
                    w.cooldown -= dt
                    if w.cooldown <= 0:
                        self._spawn_random_field(w)
                        w.cooldown = 1.0 / max(0.01, w.fire_rate)
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

    def _spawn_projectile(self, x: float, y: float, dx: float, dy: float, damage: int, lifetime: float, speed: float, color=(255, 240, 120), radius=5, despawn_on_hit=True, pierce: int = 0) -> None:
        proj = self.world.create_entity()
        self.world.add_component(proj, Position(x, y))
        self.world.add_component(proj, Velocity(dx * speed, dy * speed))
        self.world.add_component(proj, Projectile(damage, lifetime, speed, dx, dy, owner="player", despawn_on_hit=despawn_on_hit, pierce=pierce))
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
                self._spawn_projectile(cx, cy, ndx, ndy, w.damage, w.lifetime, w.speed, pierce=w.pierce)
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
                    self._spawn_projectile(cx, cy, vx, vy, w.damage, w.lifetime, w.speed, pierce=w.pierce)
        elif w.behavior == "radial_burst":
            cx, cy = ppos.x, ppos.y
            cnt = max(1, w.count)
            for i in range(cnt):
                a = (i / cnt) * 2 * math.pi
                vx, vy = math.cos(a), math.sin(a)
                self._spawn_projectile(cx, cy, vx, vy, w.damage, w.lifetime, w.speed, pierce=w.pierce)
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
        # Trim extras
        while len(spawned) > need:
            eid = spawned.pop()
            self.world.delete_entity(eid)
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
        # Re-space only when count changed
        last_count = w.state.get("last_count")
        if last_count != need:
            for i, eid in enumerate(spawned):
                orb = self.world.component_for_entity(eid, Orbit)
                if orb:
                    orb.angle_deg = (i / max(1, need)) * 360.0
        # Always update radius/speed without resetting angle
        for eid in spawned:
            orb = self.world.component_for_entity(eid, Orbit)
            if orb:
                orb.radius = w.radius
                orb.angular_speed_deg = w.angular_speed_deg
        w.state["last_count"] = need
        w.state["entities"] = spawned

    def _ensure_aura(self, owner_eid: int, ppos: Position, w: WeaponInstance) -> None:
        if w.state is None:
            w.state = {}
        eid = w.state.get("aura_eid")
        if eid is not None:
            return
        # Create a persistent field following the player
        e = self.world.create_entity()
        self.world.add_component(e, Position(ppos.x, ppos.y))
        self.world.add_component(e, Field(owner=owner_eid, radius=w.radius, dps=max(1.0, w.damage), lifetime=-1.0, follow_owner=True, color=(255, 200, 120)))
        w.state["aura_eid"] = e

    def _spawn_random_field(self, w: WeaponInstance) -> None:
        # Randomly spawn a damaging field on screen
        x = self.ctx.rng.uniform(40, max(41, self.ctx.width - 40))
        y = self.ctx.rng.uniform(40, max(41, self.ctx.height - 40))
        e = self.world.create_entity()
        self.world.add_component(e, Position(x, y))
        self.world.add_component(e, Field(owner=None, radius=w.radius, dps=max(1.0, w.damage), lifetime=max(0.3, w.lifetime), follow_owner=False, color=(120, 200, 255)))


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


class HurtCooldownSystem(esper.Processor):
    def __init__(self, ctx: GameContext) -> None:
        super().__init__()
        self.ctx = ctx

    def process(self, dt: float) -> None:
        if self.ctx.paused:
            return
        for _, hb in self.world.get_component(Hurtbox):
            if hb.cooldown > 0:
                hb.cooldown = max(0.0, hb.cooldown - dt)


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
            # Stats
            self.ctx.stats.kills += 1
            self.ctx.stats.score += 10
            # Drop XP gem with some chance
            if self.rng.random() < 0.9:
                xe = self.world.create_entity()
                self.world.add_component(xe, Position(pos.x, pos.y))
                self.world.add_component(xe, Collider(6))
                self.world.add_component(xe, Pickup("xp", 1))
                self.world.add_component(xe, Sprite((140, 255, 140), 6))
            self.world.delete_entity(e)


class EnemySpawnSystem(esper.Processor):
    def __init__(self, ctx: GameContext, width: int, height: int, base_interval: float, min_distance: float, enemy_speed: float, enemy_damage: int, enemy_color: tuple[int, int, int], offscreen_margin: int = 80) -> None:
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
        self.offscreen_margin = offscreen_margin

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
        # Spawn just outside the current camera viewport
        camx, camy = self.ctx.cam_x, self.ctx.cam_y
        vw, vh = self.width, self.height
        margin = self.offscreen_margin
        # Viewport in world coords
        left = camx - vw / 2
        right = camx + vw / 2
        top = camy - vh / 2
        bottom = camy + vh / 2
        for _ in range(50):
            side = self.rng.choice(["top", "bottom", "left", "right"])
            if side == "top":
                x = self.rng.uniform(left - margin, right + margin)
                y = top - margin
            elif side == "bottom":
                x = self.rng.uniform(left - margin, right + margin)
                y = bottom + margin
            elif side == "left":
                x = left - margin
                y = self.rng.uniform(top - margin, bottom + margin)
            else:
                x = right + margin
                y = self.rng.uniform(top - margin, bottom + margin)
            # Clamp to world bounds
            x = max(0, min(self.ctx.world_width, x))
            y = max(0, min(self.ctx.world_height, y))
            # Ensure not inside viewport
            if left <= x <= right and top <= y <= bottom:
                continue
            # Ensure at least min_distance from player
            dx, dy = x - player_pos.x, y - player_pos.y
            _, _, dist = _norm(dx, dy)
            if dist < self.min_distance:
                continue
            e = self.world.create_entity()
            self.world.add_component(e, Position(x, y))
            self.world.add_component(e, Velocity(0, 0))
            self.world.add_component(e, Enemy(damage=self.enemy_damage, speed=self.enemy_speed))
            self.world.add_component(e, Health(current=20, max_hp=20))
            self.world.add_component(e, Collider(radius=12))
            self.world.add_component(e, Faction("enemy"))
            self.world.add_component(e, Sprite(self.enemy_color, 12))
            break


class FieldSystem(esper.Processor):
    def __init__(self, ctx: GameContext) -> None:
        super().__init__()
        self.ctx = ctx

    def process(self, dt: float) -> None:
        if self.ctx.paused:
            return
        # Update follow-owner fields and apply damage
        to_delete = []
        for e, (pos, fld) in self.world.get_components(Position, Field):
            if fld.follow_owner and fld.owner is not None:
                owner_pos = self.world.component_for_entity(fld.owner, Position)
                if owner_pos is not None:
                    pos.x, pos.y = owner_pos.x, owner_pos.y
            # Apply DoT to enemies inside radius
            r2 = fld.radius * fld.radius
            for ee, (epos, _ec, _enemy, ehealth) in self.world.get_components(Position, Collider, Enemy, Health):
                if (pos.x - epos.x) ** 2 + (pos.y - epos.y) ** 2 <= r2:
                    ehealth.current -= int(fld.dps * dt)
            if fld.lifetime >= 0:
                fld.lifetime -= dt
                if fld.lifetime <= 0:
                    to_delete.append(e)
        for e in to_delete:
            self.world.delete_entity(e)


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


class ScoreSystem(esper.Processor):
    def __init__(self, ctx: GameContext) -> None:
        super().__init__()
        self.ctx = ctx

    def process(self, dt: float) -> None:
        if self.ctx.paused:
            return
        self.ctx.stats.time_sec += dt
        self.ctx.stats.score += dt  # passive score per second


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
                # Offer 3 random available cards
                keys = [k for k, v in self.cards.items() if self._is_available(k, v)]
                if not keys:
                    return
                self.ctx.levelup_choices = [self.ctx.rng.choice(keys) for _ in range(3)]
                self.ctx.paused = True
                break

    def _is_available(self, key: str, card: dict) -> bool:
        # repeatable or single-purchase check
        repeatable = bool(card.get("repeatable", False))
        if (not repeatable) and (key in self.ctx.acquired_cards):
            return False
        # Requirements
        reqs = card.get("requires")
        if not reqs:
            return True
        if isinstance(reqs, str):
            reqs = [reqs]
        # Collect owned subs/mains
        owned_subs = set()
        owned_mains = set()
        for pe, (ld,) in self.world.get_components(Loadout):
            owned_subs.update([w.key for w in ld.sub])
            if ld.main is not None:
                owned_mains.add(ld.main.key)
            break
        for r in reqs:
            if isinstance(r, str):
                if r.startswith("sub_unlocked:") or r.startswith("meta_unlocked_sub:"):
                    wkey = r.split(":", 1)[1]
                    if wkey not in self.ctx.meta_unlocked_subs and wkey not in owned_subs:
                        return False
                elif r.startswith("sub_owned:"):
                    wkey = r.split(":", 1)[1]
                    if wkey not in owned_subs:
                        return False
                elif r.startswith("not_owned_sub:"):
                    wkey = r.split(":", 1)[1]
                    if wkey in owned_subs:
                        return False
                elif r.startswith("has_main:"):
                    wkey = r.split(":", 1)[1]
                    if wkey not in owned_mains:
                        return False
                elif r.startswith("not_acquired:"):
                    ckey = r.split(":", 1)[1]
                    if ckey in self.ctx.acquired_cards:
                        return False
                # unknown reqs are ignored
        return True


def apply_card_effect(world: esper.World, player_eid: int, key: str, card: dict, ctx: GameContext) -> None:
    effect = str(card.get("effect", ""))
    amount = float(card.get("amount", 0))
    weapon_key = card.get("weapon")
    repeatable = bool(card.get("repeatable", False))

    if effect == "player_move_speed_mul":
        spd = world.component_for_entity(player_eid, Speed)
        spd.mult *= float(amount)
    elif effect == "player_max_health_add":
        h = world.component_for_entity(player_eid, Health)
        h.max_hp += int(amount)
        h.current = min(h.max_hp, h.current + int(amount))
    elif effect == "main_damage_mul":
        loadout = world.component_for_entity(player_eid, Loadout)
        if loadout.main is not None:
            loadout.main.damage = int(round(loadout.main.damage * float(amount)))
    elif effect == "main_fire_rate_mul":
        loadout = world.component_for_entity(player_eid, Loadout)
        if loadout.main is not None:
            loadout.main.fire_rate *= float(amount)
    elif effect == "weapon_count_add":
        loadout = world.component_for_entity(player_eid, Loadout)
        # Only applies to sub weapons (main remains single)
        for w in loadout.sub:
            if weapon_key is None or w.key == weapon_key:
                w.count += int(amount)
    elif effect == "sub_radius_add":
        loadout = world.component_for_entity(player_eid, Loadout)
        for w in loadout.sub:
            if weapon_key is None or w.key == weapon_key:
                w.radius += float(amount)
                # If it's an aura, update existing field entity radius
                if w.behavior == "aura" and w.state and w.state.get("aura_eid") is not None:
                    fid = w.state.get("aura_eid")
                    fld = world.component_for_entity(fid, Field)
                    if fld:
                        fld.radius = w.radius
    elif effect == "sub_angular_speed_mul":
        loadout = world.component_for_entity(player_eid, Loadout)
        for w in loadout.sub:
            if weapon_key is None or w.key == weapon_key:
                w.angular_speed_deg *= float(amount)
    elif effect == "sub_dps_mul":
        loadout = world.component_for_entity(player_eid, Loadout)
        for w in loadout.sub:
            if weapon_key is None or w.key == weapon_key:
                w.damage = int(round(w.damage * float(amount)))
                if w.behavior == "aura" and w.state and w.state.get("aura_eid") is not None:
                    fid = w.state.get("aura_eid")
                    fld = world.component_for_entity(fid, Field)
                    if fld:
                        fld.dps = max(1.0, float(w.damage))
    elif effect == "sniper_pierce_add":
        loadout = world.component_for_entity(player_eid, Loadout)
        if loadout.main is not None and loadout.main.key == "sniper":
            loadout.main.pierce += int(amount)
    elif effect == "unlock_sub":
        if weapon_key:
            ctx.unlocked_subs.add(str(weapon_key))
    elif effect == "add_sub":
        if weapon_key:
            from .content import Content  # avoid cycle
            # naive world-global content fetch isn't available; rely on card providing stats? We'll use Content again via import
            # For simplicity, reconstruct from file
            content = Content()
            wd = content.weapon_sub(weapon_key)
            if wd:
                loadout = world.component_for_entity(player_eid, Loadout)
                inst = WeaponInstance(
                    key=str(weapon_key),
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
                loadout.sub.append(inst)

    if not repeatable:
        # allow multiple levels by suffixing with a counter? For simplicity, don't block if repeatable
        ctx.acquired_cards.add(key)


class MenuInputSystem(esper.Processor):
    def __init__(self, ctx: GameContext, cards: dict[str, dict]) -> None:
        super().__init__()
        self.ctx = ctx
        self.cards = cards

    def process(self, dt: float) -> None:
        if not (self.ctx.paused and self.ctx.levelup_choices):
            return
        for event in self.ctx.events:
            if event.type not in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                continue
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
        if card.get("effect"):
            apply_card_effect(self.world, player_eid, key, card, self.ctx)
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
