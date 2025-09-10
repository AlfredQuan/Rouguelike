from __future__ import annotations

import pygame
from typing import Dict, List

from .config import Settings
from .content import Content
from .meta import ProfileStore


def run_meta_menu(settings: Settings, store: ProfileStore, content: Content) -> None:
    screen = pygame.display.set_mode((settings.window.width, settings.window.height))
    pygame.display.set_caption(f"Meta Menu — {settings.window.title}")
    clock = pygame.time.Clock()

    font = pygame.font.Font(None, 28)
    small = pygame.font.Font(None, 22)

    # Simple costs for demo
    costs: Dict[str, int] = {
        "unlock_main_switch": 2,
        # sub weapon unlock costs
        **{k: 1 for k in (content.weapons_sub or {}).keys()},
    }

    subs: List[str] = list((content.weapons_sub or {}).keys())
    selected_idx = 0
    show = True
    while show:
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                show = False
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s:
                    # start run
                    show = False
                    break
                elif event.key == pygame.K_UP:
                    selected_idx = max(0, selected_idx - 1)
                elif event.key == pygame.K_DOWN:
                    selected_idx = min(len(subs) - 1, selected_idx + 1)
                elif event.key == pygame.K_RETURN:
                    # unlock selected sub if affordable
                    if subs:
                        key = subs[selected_idx]
                        if key not in (store.profile.unlocked_subs or []):
                            cost = costs.get(key, 1)
                            if store.profile.currency >= cost:
                                store.profile.currency -= cost
                                (store.profile.unlocked_subs or []).append(key)
                                store.save()
                elif event.key == pygame.K_u:
                    # unlock main switch ability
                    if not store.profile.main_switch_unlocked:
                        cost = costs.get("unlock_main_switch", 2)
                        if store.profile.currency >= cost:
                            store.profile.currency -= cost
                            store.profile.main_switch_unlocked = True
                            store.save()
                elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    # select main if unlocked
                    if store.profile.main_switch_unlocked:
                        mains = list((content.weapons_main or content.weapons_legacy or {}).keys())
                        if mains:
                            try:
                                idx = mains.index(store.profile.selected_main)
                            except ValueError:
                                idx = 0
                            if event.key == pygame.K_LEFT:
                                idx = (idx - 1) % len(mains)
                            else:
                                idx = (idx + 1) % len(mains)
                            store.profile.selected_main = mains[idx]
                            store.save()

        # draw
        screen.fill((18, 18, 22))
        screen.blit(font.render("Meta Progression", True, (255, 255, 255)), (30, 20))
        screen.blit(small.render(f"Currency: {store.profile.currency}", True, (220, 220, 220)), (30, 56))

        # Main switch
        ms = store.profile.main_switch_unlocked
        ms_text = "Unlocked" if ms else f"Locked (U to unlock, cost {costs.get('unlock_main_switch', 2)})"
        screen.blit(small.render(f"Main Switch: {ms_text}", True, (220, 220, 220)), (30, 84))
        mains = list((content.weapons_main or content.weapons_legacy or {}).keys())
        if ms and mains:
            screen.blit(small.render(f"Selected Main: < {store.profile.selected_main} >  (Left/Right)", True, (220, 220, 220)), (30, 108))

        # Sub unlock list
        screen.blit(small.render("Unlock Sub-Weapons (Enter)", True, (220, 220, 220)), (30, 140))
        y = 166
        for i, k in enumerate(subs):
            unlocked = k in (store.profile.unlocked_subs or [])
            cost = costs.get(k, 1)
            label = f"{k} — {'Unlocked' if unlocked else f'Lock({cost})'}"
            color = (255, 255, 180) if i == selected_idx else (200, 200, 200)
            screen.blit(small.render(label, True, color), (44, y))
            y += 22

        screen.blit(small.render("Press S to start run", True, (200, 200, 255)), (30, y + 10))

        pygame.display.flip()

