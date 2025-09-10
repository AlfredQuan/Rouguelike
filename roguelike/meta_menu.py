from __future__ import annotations

import pygame
import pygame_gui
from typing import Dict, List

from .config import Settings
from .content import Content
from .meta import ProfileStore


def run_meta_menu(settings: Settings, store: ProfileStore, content: Content) -> None:
    screen = pygame.display.set_mode((settings.window.width, settings.window.height))
    pygame.display.set_caption(f"Meta Menu — {settings.window.title}")
    clock = pygame.time.Clock()
    ui = pygame_gui.UIManager((settings.window.width, settings.window.height))

    # Costs (demo): could be moved to config later
    costs: Dict[str, int] = {
        "unlock_main_switch": 2,
        **{k: 1 for k in (content.weapons_sub or {}).keys()},
    }

    # Tabs
    tab_buttons: Dict[str, pygame_gui.elements.UIButton] = {}
    current_tab = 'shop'
    for i, name in enumerate(['shop', 'achievements', 'save']):
        tab_buttons[name] = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(20 + i * 140, 20, 120, 30),
            text=name.title(),
            manager=ui
        )

    # Currency label
    currency_label = pygame_gui.elements.UILabel(
        relative_rect=pygame.Rect(settings.window.width - 240, 22, 220, 26),
        text=f"Currency: {store.profile.currency}",
        manager=ui
    )

    # Main section
    main_panel = pygame_gui.elements.UIPanel(pygame.Rect(20, 60, 400, 120), manager=ui)
    pygame_gui.elements.UILabel(pygame.Rect(10, 5, 160, 24), "Main Weapon", manager=ui, container=main_panel)
    main_switch_btn = pygame_gui.elements.UIButton(pygame.Rect(10, 35, 220, 32),
                                                   text=f"Unlock Switch (Cost {costs.get('unlock_main_switch', 2)})",
                                                   manager=ui, container=main_panel)
    def _current_mains() -> List[str]:
        data = (content.weapons_main or {})
        if not data:
            data = (content.weapons_legacy or {})
        return list(data.keys())

    def _main_options_with_names() -> List[str]:
        options: List[str] = []
        mains_dict = (content.weapons_main or content.weapons_legacy or {})
        for k in _current_mains():
            name = str(mains_dict.get(k, {}).get('name', k))
            options.append(f"{name} ({k})")
        return options

    def _parse_main_key(option_text: str) -> str:
        if option_text.endswith(')') and '(' in option_text:
            return option_text.split('(')[-1].rstrip(')')
        return option_text

    main_options = _main_options_with_names()
    start_opt = None
    if main_options:
        # try to match selected_main
        for opt in main_options:
            if _parse_main_key(opt) == store.profile.selected_main:
                start_opt = opt
                break
        if start_opt is None:
            start_opt = main_options[0]
    else:
        start_opt = store.profile.selected_main
    main_dropdown = pygame_gui.elements.UIDropDownMenu(options_list=(main_options or [start_opt]),
                                                       starting_option=start_opt,
                                                       relative_rect=pygame.Rect(240, 35, 140, 32),
                                                       manager=ui, container=main_panel)

    # Shop panel
    shop_panel = pygame_gui.elements.UIPanel(pygame.Rect(20, 190, 400, settings.window.height - 240), manager=ui)
    subs = list((content.weapons_sub or {}).keys())
    shop_list = pygame_gui.elements.UISelectionList(relative_rect=pygame.Rect(10, 10, 240, shop_panel.get_relative_rect().height - 20),
                                                    item_list=[f"{k} ({'Unlocked' if k in (store.profile.unlocked_subs or []) else 'Locked'})" for k in subs],
                                                    manager=ui, container=shop_panel)
    unlock_btn = pygame_gui.elements.UIButton(pygame.Rect(260, 10, 120, 32), text="Unlock", manager=ui, container=shop_panel)

    # Achievements panel
    ach_panel = pygame_gui.elements.UIPanel(pygame.Rect(440, 60, settings.window.width - 460, settings.window.height - 100), manager=ui)
    ach_text = pygame_gui.elements.UITextBox(html_text="", relative_rect=pygame.Rect(10, 10, ach_panel.get_relative_rect().width - 20, ach_panel.get_relative_rect().height - 20), manager=ui, container=ach_panel)

    # Save panel
    save_panel = pygame_gui.elements.UIPanel(pygame.Rect(20, 60, 400, 120), manager=ui)
    reset_btn = pygame_gui.elements.UIButton(pygame.Rect(10, 10, 160, 32), text="Reset Profile", manager=ui, container=save_panel)
    start_btn = pygame_gui.elements.UIButton(pygame.Rect(20, settings.window.height - 50, 200, 36), text="Start Run (S)", manager=ui)

    def rebuild_main_dropdown():
        nonlocal main_dropdown
        # Kill and recreate dropdown with fresh mains and current selection
        try:
            main_dropdown.kill()
        except Exception:
            pass
        ms = store.profile.selected_main
        options = _main_options_with_names()
        # pick starting option that matches selected_main
        start_opt2 = options[0] if options else ms
        for opt in options:
            if _parse_main_key(opt) == ms:
                start_opt2 = opt
                break
        main_dropdown = pygame_gui.elements.UIDropDownMenu(options_list=(options or [start_opt2]),
                                                           starting_option=start_opt2,
                                                           relative_rect=pygame.Rect(240, 35, 140, 32),
                                                           manager=ui, container=main_panel)

    def refresh_visibility():
        # Toggle panels per tab
        shop_visible = (current_tab == 'shop')
        if shop_visible:
            shop_panel.show()
            main_panel.show()
        else:
            shop_panel.hide()
            main_panel.hide()
        ach_panel.hide() if current_tab != 'achievements' else ach_panel.show()
        save_panel.hide() if current_tab != 'save' else save_panel.show()
        # Update main section controls by unlock state (only when shop is visible)
        if shop_visible:
            if store.profile.main_switch_unlocked:
                main_switch_btn.hide()
                main_dropdown.show()
            else:
                main_switch_btn.show()
                main_dropdown.hide()
        else:
            main_switch_btn.hide()
            main_dropdown.hide()
        # Update currency label
        currency_label.set_text(f"Currency: {store.profile.currency}")
        # Ensure dropdown options are always up to date when visible
        if shop_visible:
            rebuild_main_dropdown()
        # Update achievements
        defs = content.achievements or {}
        got = store.profile.achievements or {}
        lines = ["<b>Achievements</b><br><br>"]
        for key, meta in defs.items():
            name = meta.get('name', key)
            desc = meta.get('description', '')
            ok = got.get(key, False)
            lines.append(f"<font color=#{'66FF66' if ok else 'CCCCCC'}>{name} {'(Done)' if ok else ''}</font><br>{desc}<br><br>")
        totals = f"Totals — Kills {getattr(store.profile,'total_kills',0)}, Time {int(getattr(store.profile,'total_time',0))}s, Score {int(getattr(store.profile,'total_score',0))}"
        lines.append(totals)
        ach_text.set_text("".join(lines))
        # Update shop list
        shop_list.set_item_list([f"{k} ({'Unlocked' if k in (store.profile.unlocked_subs or []) else 'Locked'})" for k in subs])

    refresh_visibility()

    running = True
    while running:
        time_delta = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_s:
                running = False
            if event.type == pygame.USEREVENT:
                if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == start_btn:
                        running = False
                    elif event.ui_element == main_switch_btn:
                        cost = costs.get("unlock_main_switch", 2)
                        if not store.profile.main_switch_unlocked and store.profile.currency >= cost:
                            store.profile.currency -= cost
                            store.profile.main_switch_unlocked = True
                            store.save()
                            rebuild_main_dropdown()
                            refresh_visibility()
                    elif event.ui_element in tab_buttons.values():
                        for name, btn in tab_buttons.items():
                            if event.ui_element == btn:
                                current_tab = name
                                refresh_visibility()
                                break
                    elif event.ui_element == unlock_btn:
                        sel = shop_list.get_single_selection()
                        if sel:
                            key = sel.split(' ')[0]
                            if key not in (store.profile.unlocked_subs or []):
                                cost = costs.get(key, 1)
                                if store.profile.currency >= cost:
                                    store.profile.currency -= cost
                                    (store.profile.unlocked_subs or []).append(key)
                                    store.save()
                                    refresh_visibility()
                    elif event.ui_element == reset_btn:
                        p = store.profile
                        p.currency = 0
                        p.unlocked_subs = []
                        p.main_switch_unlocked = False
                        p.selected_main = 'basic_bolt'
                        p.achievements = {}
                        p.total_kills = 0
                        p.total_time = 0.0
                        p.total_score = 0.0
                        store.save()
                        refresh_visibility()
                elif event.user_type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED and event.ui_element == main_dropdown:
                    store.profile.selected_main = _parse_main_key(event.text)
                    store.save()

            ui.process_events(event)

        ui.update(time_delta)
        screen.fill((18, 18, 22))
        ui.draw_ui(screen)
        pygame.display.flip()
