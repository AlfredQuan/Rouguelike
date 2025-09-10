from __future__ import annotations

import pygame
import pygame_gui
from typing import Callable, Dict, List, Optional


class GameUI:
    def __init__(self, width: int, height: int, cards: Dict[str, dict]) -> None:
        self.manager = pygame_gui.UIManager((width, height))
        self.width = width
        self.height = height
        self.cards = cards

        self.pause_window: Optional[pygame_gui.elements.UIWindow] = None
        self.pause_buttons: Dict[str, pygame_gui.elements.UIButton] = {}
        self.on_resume: Optional[Callable[[], None]] = None
        self.on_return: Optional[Callable[[], None]] = None
        self.on_cheat_currency: Optional[Callable[[], None]] = None

        self.level_window: Optional[pygame_gui.elements.UIWindow] = None
        self.level_buttons: List[pygame_gui.elements.UIButton] = []
        self.level_choice_keys: List[str] = []
        self.on_choose: Optional[Callable[[str], None]] = None

        # HUD elements
        self.hud_panel: Optional[pygame_gui.elements.UIPanel] = None
        self.hp_bar: Optional[pygame_gui.elements.UIProgressBar] = None
        self.xp_bar: Optional[pygame_gui.elements.UIProgressBar] = None
        self.level_label: Optional[pygame_gui.elements.UILabel] = None
        self.score_label: Optional[pygame_gui.elements.UILabel] = None

    def process_event(self, event: pygame.event.Event) -> None:
        self.manager.process_events(event)
        if event.type == pygame.KEYDOWN and self.level_window is not None:
            if event.key in (pygame.K_1, pygame.K_KP1):
                self._choose_idx(0)
            elif event.key in (pygame.K_2, pygame.K_KP2):
                self._choose_idx(1)
            elif event.key in (pygame.K_3, pygame.K_KP3):
                self._choose_idx(2)

    def update(self, dt: float) -> None:
        self.manager.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        self.manager.draw_ui(surface)

    # Pause menu
    def open_pause(self, on_resume: Callable[[], None], on_return: Callable[[], None], on_cheat_currency: Optional[Callable[[], None]] = None) -> None:
        if self.pause_window is not None:
            return
        self.on_resume = on_resume
        self.on_return = on_return
        self.on_cheat_currency = on_cheat_currency
        w, h = 360, 220
        x, y = (self.width - w) // 2, (self.height - h) // 2
        self.pause_window = pygame_gui.elements.UIWindow(rect=pygame.Rect(x, y, w, h), window_display_title='Paused', manager=self.manager, object_id='#pause_window')
        container = self.pause_window
        self.pause_buttons['resume'] = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(20, 40, 140, 36), text='Resume (P)', manager=self.manager, container=container)
        self.pause_buttons['return'] = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(20, 86, 140, 36), text='Return to Menu', manager=self.manager, container=container)
        self.pause_buttons['cheat'] = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(20, 132, 180, 36), text='Cheat +10 Currency', manager=self.manager, container=container)

    def close_pause(self) -> None:
        if self.pause_window is not None:
            self.pause_window.kill()
            self.pause_window = None
            self.pause_buttons.clear()

    # Level-up selection
    def open_levelup(self, choices: List[str], on_choose: Callable[[str], None]) -> None:
        if self.level_window is not None:
            return
        self.level_choice_keys = choices
        self.on_choose = on_choose
        # Use a panel (no window frame) centered on screen with 3 card panels
        w, h = 640, 240
        x, y = (self.width - w) // 2, (self.height - h) // 2
        self.level_window = pygame_gui.elements.UIPanel(relative_rect=pygame.Rect(x, y, w, h), manager=self.manager, object_id='#level_panel')
        container = self.level_window
        self.level_buttons = []
        cw, ch = 190, 180
        spacing = 35
        start_x = 10
        y0 = 10
        for i, key in enumerate(choices[:3]):
            bx = start_x + i * (cw + spacing)
            # Button acts as clickable card area; texts rendered via sub-elements for wrapping
            btn = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(bx, y0, cw, ch), text="", manager=self.manager, container=container, object_id=f'#card_button_{i}')
            title = pygame_gui.elements.UILabel(relative_rect=pygame.Rect(bx + 8, y0 + 8, cw - 16, 24), text=self._card_title(key, i), manager=self.manager, container=container)
            desc = pygame_gui.elements.UITextBox(html_text=self._card_desc_html(key), relative_rect=pygame.Rect(bx + 8, y0 + 36, cw - 16, ch - 44), manager=self.manager, container=container)
            self.level_buttons.append(btn)

    def _card_label(self, key: str, idx: int) -> str:
        c = self.cards.get(key, {})
        name = c.get('name', key)
        desc = c.get('description', '')
        return f"[{idx+1}] {name}\n{desc}"

    def _card_title(self, key: str, idx: int) -> str:
        c = self.cards.get(key, {})
        name = c.get('name', key)
        return f"[{idx+1}] {name}"

    def _card_desc_html(self, key: str) -> str:
        c = self.cards.get(key, {})
        desc = c.get('description', '')
        # Simple HTML escape not implemented; assume safe text
        return desc.replace('\n', '<br>')

    def close_levelup(self) -> None:
        if self.level_window is not None:
            self.level_window.kill()
            self.level_window = None
            self.level_buttons.clear()
            self.level_choice_keys = []
            self.on_choose = None

    def handle_ui_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.USEREVENT:
            return
        if hasattr(event, 'user_type') and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            # Pause actions
            if self.pause_window is not None and event.ui_element in self.pause_buttons.values():
                if event.ui_element == self.pause_buttons.get('resume') and self.on_resume:
                    self.on_resume()
                elif event.ui_element == self.pause_buttons.get('return') and self.on_return:
                    self.on_return()
                elif event.ui_element == self.pause_buttons.get('cheat') and self.on_cheat_currency:
                    self.on_cheat_currency()
                return
            # Level up buttons
            if self.level_window is not None and self.level_buttons:
                for i, btn in enumerate(self.level_buttons):
                    if event.ui_element == btn:
                        self._choose_idx(i)
                        return

    def _choose_idx(self, i: int) -> None:
        if not self.level_choice_keys or self.on_choose is None:
            return
        i = max(0, min(i, len(self.level_choice_keys) - 1))
        key = self.level_choice_keys[i]
        self.on_choose(key)

    # HUD helpers
    def ensure_hud(self) -> None:
        if self.hud_panel is not None:
            return
        self.hud_panel = pygame_gui.elements.UIPanel(pygame.Rect(10, 10, 300, 84), manager=self.manager)
        pygame_gui.elements.UILabel(pygame.Rect(6, 0, 40, 20), text='HP', manager=self.manager, container=self.hud_panel)
        self.hp_bar = pygame_gui.elements.UIProgressBar(pygame.Rect(46, 2, 240, 16), manager=self.manager, container=self.hud_panel)
        pygame_gui.elements.UILabel(pygame.Rect(6, 28, 40, 20), text='XP', manager=self.manager, container=self.hud_panel)
        self.xp_bar = pygame_gui.elements.UIProgressBar(pygame.Rect(46, 30, 240, 16), manager=self.manager, container=self.hud_panel)
        self.level_label = pygame_gui.elements.UILabel(pygame.Rect(6, 56, 80, 20), text='Lv 1', manager=self.manager, container=self.hud_panel)
        self.score_label = pygame_gui.elements.UILabel(pygame.Rect(90, 56, 200, 20), text='Time 0s  Score 0  Kills 0', manager=self.manager, container=self.hud_panel)

    def update_hud(self, hp_curr: int, hp_max: int, xp: int, xp_need: int, level: int, time_sec: float, score: float, kills: int) -> None:
        self.ensure_hud()
        if self.hp_bar is not None and hp_max > 0:
            self.hp_bar.set_current_progress(int(100 * max(0.0, min(1.0, hp_curr / max(1, hp_max)))))
        if self.xp_bar is not None and xp_need > 0:
            self.xp_bar.set_current_progress(int(100 * max(0.0, min(1.0, xp / max(1, xp_need)))))
        if self.level_label is not None:
            self.level_label.set_text(f'Lv {level}')
        if self.score_label is not None:
            self.score_label.set_text(f'Time {int(time_sec)}s  Score {int(score)}  Kills {kills}')
