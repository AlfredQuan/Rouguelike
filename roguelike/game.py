from __future__ import annotations

import time
from typing import Tuple

from .esper_compat import esper
import pygame

from .config import Settings, load_settings
from .content import Content
from .ecs_components import Player, Health
from .context import GameContext
from .ecs_systems import (
    CollisionSystem,
    EnemyAISystem,
    EnemyDeathSystem,
    EnemySpawnSystem,
    LevelUpSystem,
    MenuInputSystem,
    InputSystem,
    MovementSystem,
    ProjectileLifetimeSystem,
    OrbitSystem,
    RenderSystem,
    WeaponFireSystem,
)
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

        self.ctx = GameContext()

        self._setup_world()

    def _setup_world(self) -> None:
        w, h = self.settings.window.width, self.settings.window.height
        gp = self.settings.gameplay
        # Player entity
        create_player(self.world, self.content, "default", (w / 2, h / 2))

        # Systems
        self.world.add_processor(InputSystem(self.ctx), priority=100)
        self.world.add_processor(MenuInputSystem(self.ctx, self.content.cards), priority=95)
        self.world.add_processor(EnemyAISystem(self.ctx), priority=90)
        self.world.add_processor(WeaponFireSystem(self.ctx), priority=85)
        self.world.add_processor(MovementSystem(self.ctx), priority=80)
        self.world.add_processor(OrbitSystem(self.ctx), priority=75)
        self.world.add_processor(ProjectileLifetimeSystem(self.ctx), priority=70)
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
        ), priority=50)
        self.world.add_processor(LevelUpSystem(self.ctx, self.content.cards), priority=45)
        self.world.add_processor(RenderSystem(self.ctx, self.content.cards, self.screen, w, h), priority=0)

    def run(self) -> None:
        running = True
        fps = self.settings.window.fps
        while running:
            dt_ms = self.clock.tick(fps)
            dt = dt_ms / 1000.0
            # Pump events; processors handle them. Check for global quit without draining queue.
            pygame.event.pump()
            if pygame.event.peek(pygame.QUIT):
                running = False
            keys = pygame.key.get_pressed()
            if keys[pygame.K_ESCAPE]:
                running = False

            self.world.process(dt)

            # Check player death and grant small currency for demo
            for _, (pl, h) in self.world.get_components(Player, Health):
                if h.current <= 0:
                    self.profile.currency += 1
                    self.profile_store.save()
                    running = False
                    break

            pygame.display.flip()

    @staticmethod
    def init_pygame():
        pygame.init()


def run_game() -> None:
    Game.init_pygame()
    settings = load_settings()
    game = Game(settings)
    game.run()
