from __future__ import annotations

import time
from typing import Tuple

from .esper_compat import esper
import pygame

from .config import Settings, load_settings
from .content import Content
from .ecs_components import Player, Health, Position, Loadout
from .context import GameContext
from .ecs_systems import (
    CollisionSystem,
    EnemyAISystem,
    EnemyDeathSystem,
    EnemySpawnSystem,
    LevelUpSystem,
    WeaponFireSystem,
    InputSystem,
    MovementSystem,
    ProjectileLifetimeSystem,
    HurtCooldownSystem,
    OrbitSystem,
    FieldSystem,
    ScoreSystem,
    PickupMagnetSystem,
    PickupCleanupSystem,
    ProjectileCleanupSystem,
    WeaponSanitySystem,
    RenderSystem,
)
from .cheats import CheatSystem
from .factories import create_player
from .meta import ProfileStore
from .ui import GameUI
from .ecs_systems import apply_card_effect


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
        self.world.add_processor(CheatSystem(self.ctx, self.content), priority=92)
        self.world.add_processor(EnemyAISystem(self.ctx), priority=90)
        self.world.add_processor(WeaponFireSystem(self.ctx), priority=85)
        self.world.add_processor(MovementSystem(self.ctx), priority=80)
        self.world.add_processor(OrbitSystem(self.ctx), priority=75)
        self.world.add_processor(FieldSystem(self.ctx), priority=74)
        self.world.add_processor(ScoreSystem(self.ctx), priority=72)
        self.world.add_processor(PickupMagnetSystem(self.ctx, self.settings.gameplay.pickup_magnet_radius), priority=71)
        self.world.add_processor(ProjectileLifetimeSystem(self.ctx), priority=70)
        self.world.add_processor(ProjectileCleanupSystem(self.ctx, self.settings.gameplay.projectile_max_count), priority=69)
        self.world.add_processor(HurtCooldownSystem(self.ctx), priority=68)
        self.world.add_processor(WeaponSanitySystem(self.ctx, self.content), priority=65)
        self.world.add_processor(CollisionSystem(self.ctx, w, h), priority=60)
        self.world.add_processor(EnemyDeathSystem(self.ctx, __import__("random").Random(1337)), priority=55)
        self.world.add_processor(EnemySpawnSystem(
            self.ctx,
            self.content,
            width=w,
            height=h,
            base_interval=self.settings.spawning.enemy_spawn_interval,
            min_distance=self.settings.gameplay.enemy_spawn_distance_min,
            offscreen_margin=self.settings.spawning.offscreen_margin,
        ), priority=50)
        self.world.add_processor(PickupCleanupSystem(self.ctx, self.settings.gameplay.pickup_max_count), priority=48)
        self.world.add_processor(LevelUpSystem(self.ctx, self.content.cards), priority=45)
        self.world.add_processor(RenderSystem(self.ctx, self.content.cards, self.screen, w, h, self.settings.world.grid_size), priority=0)

    def run(self) -> None:
        running = True
        fps = self.settings.window.fps
        # In-run UI (pygame_gui)
        ui = GameUI(self.settings.window.width, self.settings.window.height, self.content.cards)
        while running:
            dt_ms = self.clock.tick(fps)
            dt = dt_ms / 1000.0
            # Event handling: collect but let systems use them
            events = pygame.event.get()
            self.ctx.events = events
            for event in events:
                ui.process_event(event)
                ui.handle_ui_event(event)
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_p and not self.ctx.levelup_choices:
                        if ui.pause_window is None:
                            self.ctx.paused = True
                            def _resume():
                                self.ctx.paused = False
                                ui.close_pause()
                            def _ret():
                                ui.close_pause()
                                # End run
                                nonlocal running
                                running = False
                            # Cheat actions mapping
                            def add_currency():
                                profile = getattr(self.world, 'profile', None)
                                store = getattr(self.world, 'profile_store', None)
                                if profile is not None and store is not None:
                                    profile.currency += 10
                                    store.save()
                            def add_xp():
                                for _, exp in self.world.get_component(__import__('roguelike.ecs_components', fromlist=['Experience']).Experience):
                                    exp.xp += 10
                            def heal():
                                for _, h in self.world.get_component(Health):
                                    h.current = h.max_hp
                            def unlock_all_subs():
                                for k in (self.content.weapons_sub or {}).keys():
                                    self.ctx.meta_unlocked_subs.add(k)
                                store = getattr(self.world, 'profile_store', None)
                                profile = getattr(self.world, 'profile', None)
                                if store and profile is not None:
                                    s = set(profile.unlocked_subs or [])
                                    s.update(self.ctx.meta_unlocked_subs)
                                    profile.unlocked_subs = sorted(list(s))
                                    store.save()
                            def add_sub(key: str):
                                # reuse cheat method
                                from .cheats import CheatSystem
                                cs = CheatSystem(self.ctx, self.content)
                                cs.world = self.world
                                cs._add_sub(key)
                            def set_main(key: str):
                                from .cheats import CheatSystem
                                cs = CheatSystem(self.ctx, self.content)
                                cs.world = self.world
                                cs._add_main(key)
                                # persist selection
                                profile = getattr(self.world, 'profile', None)
                                store = getattr(self.world, 'profile_store', None)
                                if profile and store:
                                    profile.selected_main = key
                                    store.save()
                            def force_cards():
                                from .ecs_systems import LevelUpSystem as _L
                                cards = self.content.cards
                                lus = _L(self.ctx, cards)
                                lus.world = self.world
                                avail = [k for k, v in cards.items() if lus._is_available(k, v)]
                                if avail:
                                    self.ctx.levelup_choices = [self.ctx.rng.choice(avail) for _ in range(3)]
                                    self.ctx.paused = True
                                    ui.open_levelup(self.ctx.levelup_choices, _apply)
                            cheat_actions = {
                                '+10 Currency': add_currency,
                                '+10 XP': add_xp,
                                'Heal Full': heal,
                                'Unlock All Subs': unlock_all_subs,
                                'Add Orbital': lambda: add_sub('orbital_blade'),
                                'Add Aura': lambda: add_sub('aura_garlic'),
                                'Add Storm': lambda: add_sub('random_storm'),
                                'Main Sniper': lambda: set_main('sniper'),
                                'Main Tri': lambda: set_main('tri_shot'),
                                'Main Nova': lambda: set_main('nova_burst'),
                                'Main Rapid': lambda: set_main('rapid_blaster'),
                                'Force Cards': force_cards,
                            }
                            ui.open_pause(on_resume=_resume, on_return=_ret, cheat_actions=cheat_actions)
                        else:
                            # Toggle off
                            self.ctx.paused = False
                            ui.close_pause()

            # Camera: follow player
            for _, (ppos, _pl) in self.world.get_components(Position, Player):
                self.ctx.cam_x, self.ctx.cam_y = ppos.x, ppos.y
                break

            # Open level-up UI if choices available
            if self.ctx.levelup_choices and ui.level_window is None:
                choices = list(self.ctx.levelup_choices)
                def _apply(key: str):
                    # find player
                    player_eid = None
                    for e, _ in self.world.get_component(Player):
                        player_eid = e
                        break
                    if player_eid is None:
                        return
                    card = self.content.cards.get(key, {})
                    apply_card_effect(self.world, player_eid, key, card, self.ctx)
                    # 清空玩家速度，避免卡片选择后速度残留导致“自动向某方向移动”
                    from .ecs_components import Velocity
                    for _, (v,) in self.world.get_components(Velocity):
                        v.x = 0.0
                        v.y = 0.0
                    self.ctx.levelup_choices = None
                    self.ctx.paused = False
                    ui.close_levelup()
                # Remain paused while window open
                self.ctx.paused = True
                ui.open_levelup(choices, _apply)

            self.world.process(dt)
            # Show wave/boss banners when requested by systems
            if self.ctx.banner_time_left > 0 and self.ctx.banner_text:
                # Consume context banner and hand off to UI
                ui.show_banner(self.ctx.banner_text, self.ctx.banner_time_left)
                self.ctx.banner_text = ""
                self.ctx.banner_time_left = 0.0
            # Update HUD via pygame_gui
            hp_curr = hp_max = xp = xp_need = level = 0
            for _, (h, exp) in self.world.get_components(Health, __import__('roguelike.ecs_components', fromlist=['Experience']).Experience):
                hp_curr, hp_max = h.current, h.max_hp
                xp, level = exp.xp, exp.level
                xp_need = 5 + (exp.level - 1) * 2
                break
            ui.update_hud(hp_curr, hp_max, xp, xp_need, level, self.ctx.stats.time_sec, self.ctx.stats.score, self.ctx.stats.kills)
            # Wave timer text
            wave_text = self._compute_wave_text()
            ui.update_wave_timer(wave_text)
            # Update weapons display via pygame_gui
            main_name = ""
            sub_names: list[str] = []
            for _, (ld,) in self.world.get_components(Loadout):
                if ld.main is not None:
                    wdef = (self.content.weapons_main or self.content.weapons_legacy).get(ld.main.key, {})
                    main_name = str(wdef.get("name", ld.main.key))
                for w in ld.sub:
                    sd = (self.content.weapons_sub or {}).get(w.key, {})
                    sub_names.append(str(sd.get("name", w.key)))
                break
            ui.update_weapons(main_name, sub_names)
            ui.update(dt)

            # Check player death and end run
            for _, (pl, h) in self.world.get_components(Player, Health):
                if h.current <= 0:
                    running = False
                    break

            ui.draw(self.screen)
            pygame.display.flip()

    @staticmethod
    def init_pygame():
        pygame.init()

    def _compute_wave_text(self) -> str:
        waves = (self.content.waves or {}).get('waves', [])
        t = self.ctx.stats.time_sec
        if not waves:
            return "Wave -"
        cur_idx = -1
        cur = None
        for i, w in enumerate(waves):
            start = float(w.get('start', 0))
            duration = float(w.get('duration', 0))
            if t >= start and t < start + duration:
                cur_idx = i
                cur = w
                break
        if cur is None:
            # After last wave; show final wave
            cur_idx = len(waves) - 1
            cur = waves[-1]
        start = float(cur.get('start', 0))
        duration = float(cur.get('duration', 0))
        elapsed = max(0.0, t - start)
        remain = max(0.0, duration - elapsed) if duration > 0 else 0.0
        # Surge countdown if present
        surge_every = float(cur.get('surge_every', 0))
        surge_txt = ""
        if surge_every > 0:
            # time to next surge
            since = elapsed % surge_every
            to_next = surge_every - since if since > 0 else 0
            surge_txt = f" • Horde in {int(to_next)}s"
        # Boss timing
        boss = cur.get('boss')
        boss_txt = ""
        if boss:
            if boss.get('at_end', False):
                boss_txt = " • Boss at wave end"
            else:
                at = float(boss.get('at', -1))
                if at >= 0:
                    bt = max(0, int(at - t))
                    boss_txt = f" • Boss in {bt}s"
        return f"Wave {cur_idx+1}: {int(remain)}s left{surge_txt}{boss_txt}"

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
        # Post-run screen (pygame_gui)
        screen = pygame.display.get_surface()
        import pygame_gui
        from pathlib import Path
        theme_path = Path('assets/ui/theme.json')
        ui = pygame_gui.UIManager((settings.window.width, settings.window.height), theme_path if theme_path.exists() else None)
        panel = pygame_gui.elements.UIPanel(pygame.Rect(100, 80, settings.window.width - 200, settings.window.height - 160), manager=ui)
        pygame_gui.elements.UILabel(pygame.Rect(10, 10, 200, 30), text='Run Over', manager=ui, container=panel)
        info = [
            f"Time: {game.ctx.stats.time_sec:.1f}s",
            f"Kills: {game.ctx.stats.kills}",
            f"Score: {int(game.ctx.stats.score)}",
            f"Currency Earned: +{earned} (Total: {profile.currency})",
        ]
        y = 50
        for line in info:
            pygame_gui.elements.UILabel(pygame.Rect(10, y, panel.get_relative_rect().width - 20, 24), text=line, manager=ui, container=panel)
            y += 26
        btn_return = pygame_gui.elements.UIButton(pygame.Rect(10, y + 10, 160, 36), text='Return to Menu', manager=ui, container=panel)
        btn_quit = pygame_gui.elements.UIButton(pygame.Rect(180, y + 10, 100, 36), text='Quit', manager=ui, container=panel)
        clock = pygame.time.Clock()
        showing = True
        while showing:
            time_delta = clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == btn_return:
                        showing = False
                        break
                    if event.ui_element == btn_quit:
                        return
                ui.process_events(event)
            ui.update(time_delta)
            screen.fill((16, 16, 20))
            ui.draw_ui(screen)
            pygame.display.flip()
