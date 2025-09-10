from __future__ import annotations

import pygame
import pygame_gui
from pathlib import Path
from typing import Callable, Dict, List, Optional


class GameUI:
    def __init__(self, width: int, height: int, cards: Dict[str, dict]) -> None:
        theme_path = Path('assets/ui/theme.json')
        self.manager = pygame_gui.UIManager((width, height), theme_path if theme_path.exists() else None)
        self.width = width
        self.height = height
        self.cards = cards

        self.pause_window: Optional[pygame_gui.elements.UIWindow] = None
        self.pause_buttons: Dict[str, pygame_gui.elements.UIButton] = {}
        self.on_resume: Optional[Callable[[], None]] = None
        self.on_return: Optional[Callable[[], None]] = None
        self._cheat_callbacks: Dict[str, Callable[[], None]] = {}

        self.level_window: Optional[object] = None  # can be a panel or None when using free elements
        self.level_buttons: List[pygame_gui.elements.UIButton] = []
        self.level_choice_keys: List[str] = []
        self.on_choose: Optional[Callable[[str], None]] = None
        self.level_elements: List[pygame_gui.core.interfaces.gui_element_interface.IUIElementInterface] = []
        self.level_card_rects: List[pygame.Rect] = []

        # HUD elements
        self.hud_panel: Optional[pygame_gui.elements.UIPanel] = None
        self.hp_bar: Optional[pygame_gui.elements.UIProgressBar] = None
        self.xp_bar: Optional[pygame_gui.elements.UIProgressBar] = None
        self.level_label: Optional[pygame_gui.elements.UILabel] = None
        self.score_label: Optional[pygame_gui.elements.UILabel] = None
        # Weapons display (inside HUD)
        self.weapons_main_label: Optional[pygame_gui.elements.UILabel] = None
        self.weapons_sub_label: Optional[pygame_gui.elements.UILabel] = None
        # Banner
        self.banner_label: Optional[pygame_gui.elements.UILabel] = None
        self.banner_time_left: float = 0.0
        # Wave timer
        self.wave_label: Optional[pygame_gui.elements.UILabel] = None

    def process_event(self, event: pygame.event.Event) -> None:
        self.manager.process_events(event)
        if event.type == pygame.KEYDOWN and self.level_window is not None:
            if event.key in (pygame.K_1, pygame.K_KP1):
                self._choose_idx(0)
            elif event.key in (pygame.K_2, pygame.K_KP2):
                self._choose_idx(1)
            elif event.key in (pygame.K_3, pygame.K_KP3):
                self._choose_idx(2)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.level_window is not None:
            mx, my = event.pos
            for i, r in enumerate(self.level_card_rects):
                if r.collidepoint(mx, my):
                    self._choose_idx(i)
                    break

    def update(self, dt: float) -> None:
        self.manager.update(dt)
        # Banner timer
        if self.banner_time_left > 0:
            self.banner_time_left -= dt
            if self.banner_time_left <= 0 and self.banner_label is not None:
                self.banner_label.kill()
                self.banner_label = None

    def draw(self, surface: pygame.Surface) -> None:
        self.manager.draw_ui(surface)

    # Pause menu
    def open_pause(self, on_resume: Callable[[], None], on_return: Callable[[], None], cheat_actions: Optional[Dict[str, Callable[[], None]]] = None) -> None:
        if self.pause_window is not None:
            return
        self.on_resume = on_resume
        self.on_return = on_return
        w, h = 520, 360
        x, y = (self.width - w) // 2, (self.height - h) // 2
        self.pause_window = pygame_gui.elements.UIWindow(rect=pygame.Rect(x, y, w, h), window_display_title='Paused', manager=self.manager, object_id='#pause_window')
        container = self.pause_window
        self.pause_buttons['resume'] = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(20, 40, 160, 36), text='Resume (P)', manager=self.manager, container=container)
        self.pause_buttons['return'] = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(20, 86, 160, 36), text='Return to Menu', manager=self.manager, container=container)
        # Cheats grid
        if cheat_actions:
            col = 0
            row = 0
            for label, fn in cheat_actions.items():
                key = f'cheat_{col}_{row}'
                bx = 200 + col * 160
                by = 40 + row * 46
                self.pause_buttons[key] = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(bx, by, 150, 36), text=label, manager=self.manager, container=container)
                self._cheat_callbacks[key] = fn
                row += 1
                if row >= 6:
                    row = 0
                    col += 1

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
        # Create three standalone card elements centered on the screen (no outer frame)
        w, h = 640, 200
        x, y = (self.width - w) // 2, (self.height - h) // 2
        # Mark level UI as open
        self.level_window = True
        self.level_buttons = []
        self.level_card_rects = []
        cw, ch = 190, 180
        spacing = 35
        start_x = 10
        y0 = 10
        for i, key in enumerate(choices[:3]):
            bx = start_x + i * (cw + spacing)
            card_rect = pygame.Rect(x + bx, y + y0, cw, ch)
            # Use a panel as the card background container
            panel = pygame_gui.elements.UIPanel(relative_rect=card_rect, manager=self.manager, object_id=f'#card_panel_{i}')
            title = pygame_gui.elements.UILabel(relative_rect=pygame.Rect(8, 8, cw - 16, 24), text=self._card_title(key, i), manager=self.manager, container=panel)
            desc = pygame_gui.elements.UITextBox(html_text=self._card_desc_html(key), relative_rect=pygame.Rect(8, 36, cw - 16, ch - 44), manager=self.manager, container=panel)
            self.level_elements.extend([panel])  # killing panel will kill children
            self.level_card_rects.append(card_rect)

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
        # Kill any created elements
        if self.level_elements:
            for el in self.level_elements:
                try:
                    el.kill()
                except Exception:
                    pass
        self.level_window = None
        self.level_elements = []
        self.level_buttons.clear()
        self.level_choice_keys = []
        self.on_choose = None
        self.level_card_rects = []

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
                else:
                    # find cheat button label
                    for name, btn in self.pause_buttons.items():
                        if btn == event.ui_element and name.startswith('cheat_'):
                            fn = self._cheat_callbacks.get(name)
                            if fn:
                                fn()
                            break
                return
            # Level up uses mouse hit-testing on panels; no button event needed

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
        self.hud_panel = pygame_gui.elements.UIPanel(pygame.Rect(10, 10, 360, 90), manager=self.manager)
        pygame_gui.elements.UILabel(pygame.Rect(4, 0, 24, 18), text='HP', manager=self.manager, container=self.hud_panel)
        self.hp_bar = pygame_gui.elements.UIProgressBar(pygame.Rect(28, 2, 200, 14), manager=self.manager, container=self.hud_panel)
        pygame_gui.elements.UILabel(pygame.Rect(4, 20, 24, 18), text='XP', manager=self.manager, container=self.hud_panel)
        self.xp_bar = pygame_gui.elements.UIProgressBar(pygame.Rect(28, 22, 200, 14), manager=self.manager, container=self.hud_panel)
        self.level_label = pygame_gui.elements.UILabel(pygame.Rect(236, 0, 52, 18), text='Lv 1', manager=self.manager, container=self.hud_panel)
        self.score_label = pygame_gui.elements.UILabel(pygame.Rect(236, 20, 120, 18), text='T0 S0 K0', manager=self.manager, container=self.hud_panel)
        # Weapons inside HUD — compact
        self.weapons_main_label = pygame_gui.elements.UILabel(pygame.Rect(4, 42, 348, 18), text='Main: -', manager=self.manager, container=self.hud_panel)
        self.weapons_sub_label = pygame_gui.elements.UILabel(pygame.Rect(4, 62, 348, 18), text='Subs: -', manager=self.manager, container=self.hud_panel)
        # wave label is separate at top-right
        if self.wave_label is None:
            self.wave_label = pygame_gui.elements.UILabel(pygame.Rect(self.width - 260, 10, 250, 20), text='Wave -', manager=self.manager)

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

    def update_weapons(self, main_name: str, sub_names: list[str]) -> None:
        self.ensure_hud()
        if self.weapons_main_label is not None:
            self.weapons_main_label.set_text(f'Main: {main_name or "-"}')
        if self.weapons_sub_label is not None:
            subs_text = ", ".join(sub_names) if sub_names else "-"
            self.weapons_sub_label.set_text(f'Subs: {subs_text}')

    def show_banner(self, text: str, seconds: float = 3.0) -> None:
        if not text:
            return
        # Create/replace top-center banner label
        if self.banner_label is not None:
            try:
                self.banner_label.kill()
            except Exception:
                pass
        width = min(600, self.width - 40)
        x = (self.width - width) // 2
        self.banner_label = pygame_gui.elements.UILabel(pygame.Rect(x, 10, width, 30), text=text, manager=self.manager)
        self.banner_time_left = seconds

    def update_wave_timer(self, text: str) -> None:
        self.ensure_hud()
        if self.wave_label is not None:
            self.wave_label.set_text(text)
