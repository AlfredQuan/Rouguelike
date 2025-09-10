from __future__ import annotations

import time
from typing import Tuple

from .esper_compat import esper
import pygame

from .config import Settings, load_settings
from .content import Content
from .ecs_components import Player, Health, Position
from .context import GameContext
from .ecs_systems import (
    CollisionSystem,
    EnemyAISystem,
    EnemyDeathSystem,
    EnemySpawnSystem,
    LevelUpSystem,
    MenuInputSystem,
    WeaponFireSystem,
    InputSystem,
    MovementSystem,
    ProjectileLifetimeSystem,
    HurtCooldownSystem,
    OrbitSystem,
    FieldSystem,
    ScoreSystem,
    RenderSystem,
)
from .cheats import CheatSystem
from .factories import create_player
from .meta import ProfileStore


class Game:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.content = Content()
        self.world = esper.World()
        self.clock = pygame.time.Clock()
        self.screen = pygame.display.set_mode((settings.window.width, settings.window.height))
        pygame.display.set_caption(settings.window.title)

        self.profile_store = ProfileStore(settings.meta.save_path)
        self.profile = self.profile_store.load(starting_currency=settings.meta.starting_currency)
        # Expose meta on world for systems like CheatSystem
        setattr(self.world, "profile_store", self.profile_store)
        setattr(self.world, "profile", self.profile)

        self.ctx = GameContext()
        self.ctx.width = settings.window.width
        self.ctx.height = settings.window.height
        self.ctx.world_width = settings.world.width
        self.ctx.world_height = settings.world.height
        self.ctx.grid_size = settings.world.grid_size
        # Pull meta-unlocked subs into context
        self.ctx.meta_unlocked_subs = set(self.profile.unlocked_subs or [])

        self._setup_world()

    def _setup_world(self) -> None:
        w, h = self.settings.window.width, self.settings.window.height
        gp = self.settings.gameplay
        # Player entity (single main from meta selection)
        create_player(self.world, self.content, "default", (w / 2, h / 2), main_key=self.profile.selected_main)
        # Populate world with obstacles and pickups
        self._populate_world()

        # Systems
        self.world.add_processor(InputSystem(self.ctx), priority=100)
        self.world.add_processor(MenuInputSystem(self.ctx, self.content.cards), priority=95)
        self.world.add_processor(CheatSystem(self.ctx, self.content), priority=92)
        self.world.add_processor(EnemyAISystem(self.ctx), priority=90)
        self.world.add_processor(WeaponFireSystem(self.ctx), priority=85)
        self.world.add_processor(MovementSystem(self.ctx), priority=80)
        self.world.add_processor(OrbitSystem(self.ctx), priority=75)
        self.world.add_processor(FieldSystem(self.ctx), priority=74)
        self.world.add_processor(ScoreSystem(self.ctx), priority=72)
        self.world.add_processor(ProjectileLifetimeSystem(self.ctx), priority=70)
        self.world.add_processor(HurtCooldownSystem(self.ctx), priority=68)
        self.world.add_processor(CollisionSystem(self.ctx, w, h), priority=60)
        self.world.add_processor(EnemyDeathSystem(self.ctx, __import__("random").Random(1337)), priority=55)
        self.world.add_processor(EnemySpawnSystem(
            self.ctx,
            width=w,
            height=h,
            base_interval=self.settings.spawning.enemy_spawn_interval,
            min_distance=self.settings.gameplay.enemy_spawn_distance_min,
            enemy_speed=self.settings.gameplay.enemy_base_speed,
            enemy_damage=self.settings.gameplay.enemy_damage,
            enemy_color=self.settings.gameplay.enemy_color,
            offscreen_margin=self.settings.spawning.offscreen_margin,
        ), priority=50)
        self.world.add_processor(LevelUpSystem(self.ctx, self.content.cards), priority=45)
        self.world.add_processor(RenderSystem(self.ctx, self.content.cards, self.screen, w, h, self.settings.world.grid_size), priority=0)

    def run(self) -> None:
        running = True
        fps = self.settings.window.fps
        while running:
            dt_ms = self.clock.tick(fps)
            dt = dt_ms / 1000.0
            # Event handling: collect but let systems use them
            events = pygame.event.get()
            self.ctx.events = events
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_p and not self.ctx.levelup_choices:
                        self.ctx.paused = not self.ctx.paused

            # Camera: follow player
            for _, (ppos, _pl) in self.world.get_components(Position, Player):
                self.ctx.cam_x, self.ctx.cam_y = ppos.x, ppos.y
                break

            self.world.process(dt)

            # Check player death and end run
            for _, (pl, h) in self.world.get_components(Player, Health):
                if h.current <= 0:
                    running = False
                    break

            pygame.display.flip()

    @staticmethod
    def init_pygame():
        pygame.init()

    def _populate_world(self) -> None:
        import random
        from .ecs_components import Obstacle, Collider, Sprite, Position, Pickup
        rng = random.Random(123)
        # Obstacles as circles
        for _ in range(20):
            x = rng.uniform(100, self.ctx.world_width - 100)
            y = rng.uniform(100, self.ctx.world_height - 100)
            r = rng.randint(16, 28)
            e = self.world.create_entity()
            self.world.add_component(e, Position(x, y))
            self.world.add_component(e, Collider(radius=r))
            self.world.add_component(e, Obstacle())
            self.world.add_component(e, Sprite((110, 110, 130), r))
        # Health pickups
        for _ in range(8):
            x = rng.uniform(80, self.ctx.world_width - 80)
            y = rng.uniform(80, self.ctx.world_height - 80)
            e = self.world.create_entity()
            self.world.add_component(e, Position(x, y))
            self.world.add_component(e, Collider(radius=7))
            self.world.add_component(e, Pickup("heal", 10))
            self.world.add_component(e, Sprite((255, 120, 140), 7))


def run_game() -> None:
    Game.init_pygame()
    settings = load_settings()
    from .meta_menu import run_meta_menu
    store = ProfileStore(settings.meta.save_path)
    profile = store.load(starting_currency=settings.meta.starting_currency)
    while True:
        # Meta menu
        content = Content()
        run_meta_menu(settings, store, content)
        # Start a run
        game = Game(settings)
        game.run()
        # Convert score to currency and show summary
        # Economy conversion from settings
        earned = int(
            game.ctx.stats.score * settings.economy.score_to_currency
            + game.ctx.stats.kills * settings.economy.kills_to_currency
            + game.ctx.stats.time_sec * settings.economy.time_to_currency
        )
        if earned < 0:
            earned = 0
        profile.currency += earned
        # Update totals for achievements
        profile.total_kills = getattr(profile, 'total_kills', 0) + game.ctx.stats.kills
        profile.total_time = getattr(profile, 'total_time', 0.0) + game.ctx.stats.time_sec
        profile.total_score = getattr(profile, 'total_score', 0.0) + game.ctx.stats.score
        # Evaluate achievements
        ach_defs = content.achievements
        unlocked = getattr(profile, 'achievements', {}) or {}
        def _check(expr: str) -> bool:
            try:
                return bool(eval(expr, {}, {
                    'total_kills': profile.total_kills,
                    'total_time': profile.total_time,
                    'total_score': profile.total_score,
                }))
            except Exception:
                return False
        if ach_defs:
            for key, meta in ach_defs.items():
                if not unlocked.get(key):
                    cond = str(meta.get('condition', ''))
                    if cond and _check(cond):
                        unlocked[key] = True
        profile.achievements = unlocked
        store.save()
        # Post-run screen
        screen = pygame.display.get_surface()
        clock = pygame.time.Clock()
        font = pygame.font.Font(None, 28)
        big = pygame.font.Font(None, 36)
        showing = True
        while showing:
            clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        showing = False
                        break
                    if event.key == pygame.K_q:
                        return
            screen.fill((16, 16, 20))
            screen.blit(big.render("Run Over", True, (255,255,255)), (40, 40))
            lines = [
                f"Time: {game.ctx.stats.time_sec:.1f}s",
                f"Kills: {game.ctx.stats.kills}",
                f"Score: {int(game.ctx.stats.score)}",
                f"Currency Earned: +{earned} (Total: {profile.currency})",
                "Press Enter to return to Meta Menu, Q to quit",
            ]
            y = 90
            for line in lines:
                screen.blit(font.render(line, True, (230,230,230)), (40, y))
                y += 26
            pygame.display.flip()
