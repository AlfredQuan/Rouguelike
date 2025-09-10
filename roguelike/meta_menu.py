from __future__ import annotations

import pygame
from typing import Dict, List, Tuple

from .config import Settings
from .content import Content
from .meta import ProfileStore


def run_meta_menu(settings: Settings, store: ProfileStore, content: Content) -> None:
    screen = pygame.display.set_mode((settings.window.width, settings.window.height))
    pygame.display.set_caption(f"Meta Menu — {settings.window.title}")
    clock = pygame.time.Clock()

    font = pygame.font.Font(None, 28)
    small = pygame.font.Font(None, 22)

    # Costs (demo): can be moved to config later
    costs: Dict[str, int] = {
        "unlock_main_switch": 2,
        **{k: 1 for k in (content.weapons_sub or {}).keys()},
    }

    subs: List[str] = list((content.weapons_sub or {}).keys())
    mains: List[str] = list((content.weapons_main or content.weapons_legacy or {}).keys())
    tab = 'shop'  # 'shop', 'achievements', 'save'

    def tab_rects() -> Dict[str, pygame.Rect]:
        names = ['shop', 'achievements', 'save']
        return {n: pygame.Rect(20 + i*140, 20, 120, 28) for i, n in enumerate(names)}

    def main_rects() -> Tuple[pygame.Rect, pygame.Rect]:
        left = pygame.Rect(30, 110, 24, 24)
        right = pygame.Rect(300, 110, 24, 24)
        return left, right

    def list_rect(i: int) -> pygame.Rect:
        return pygame.Rect(30, 180 + i * 26, 380, 22)

    running = True
    while running:
        clock.tick(60)
        mx, my = pygame.mouse.get_pos()
        mpressed = pygame.mouse.get_pressed()[0]
        clicked = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s:
                    running = False
                if event.key == pygame.K_u and not store.profile.main_switch_unlocked:
                    cost = costs.get("unlock_main_switch", 2)
                    if store.profile.currency >= cost:
                        store.profile.currency -= cost
                        store.profile.main_switch_unlocked = True
                        store.save()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True
                # Switch tabs
                for name, rect in tab_rects().items():
                    if rect.collidepoint(mx, my):
                        tab = name
                        break

        # Interactions
        lrect, rrect = main_rects()
        if clicked and store.profile.main_switch_unlocked and mains:
            if lrect.collidepoint(mx, my) or rrect.collidepoint(mx, my):
                try:
                    idx = mains.index(store.profile.selected_main)
                except ValueError:
                    idx = 0
                if lrect.collidepoint(mx, my):
                    idx = (idx - 1) % len(mains)
                else:
                    idx = (idx + 1) % len(mains)
                store.profile.selected_main = mains[idx]
                store.save()

        if tab == 'shop':
            for i, key in enumerate(subs):
                rect = list_rect(i)
                unlocked = key in (store.profile.unlocked_subs or [])
                if clicked and rect.collidepoint(mx, my) and not unlocked:
                    cost = costs.get(key, 1)
                    if store.profile.currency >= cost:
                        store.profile.currency -= cost
                        (store.profile.unlocked_subs or []).append(key)
                        store.save()
        elif tab == 'save':
            # Reset profile button
            reset_rect = pygame.Rect(30, 180, 200, 28)
            if clicked and reset_rect.collidepoint(mx, my):
                # Minimal reset (keep currency for safety? here reset all)
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

        # Draw
        screen.fill((18, 18, 22))
        # Tabs
        tabs = tab_rects()
        for name, rect in tabs.items():
            pygame.draw.rect(screen, (50, 50, 60), rect)
            if tab == name:
                pygame.draw.rect(screen, (200, 200, 220), rect, 2)
            screen.blit(small.render(name.title(), True, (230, 230, 230)), (rect.x + 10, rect.y + 4))
        screen.blit(small.render(f"Currency: {store.profile.currency}", True, (220, 220, 220)), (screen.get_width()-220, 26))

        # Main weapon section
        screen.blit(small.render("Main Weapon", True, (220, 220, 220)), (30, 78))
        ms = store.profile.main_switch_unlocked
        ms_text = "Unlocked" if ms else f"Locked (click to unlock: cost {costs.get('unlock_main_switch', 2)} or press U)"
        ms_label = small.render(f"Switch: {ms_text}", True, (200, 200, 210))
        screen.blit(ms_label, (30, 96))

        # Draw main selection arrows and current main
        if ms and mains:
            lrect, rrect = main_rects()
            pygame.draw.polygon(screen, (240, 240, 200), [(lrect.right, lrect.top), (lrect.left, lrect.top + lrect.height // 2), (lrect.right, lrect.bottom)])
            pygame.draw.polygon(screen, (240, 240, 200), [(rrect.left, rrect.top), (rrect.right, rrect.top + rrect.height // 2), (rrect.left, rrect.bottom)])
            current = store.profile.selected_main
            screen.blit(small.render(f"< {current} >", True, (255, 255, 255)), (60, 112))
        else:
            # Click to unlock main switch via label
            if pygame.mouse.get_pressed()[0]:
                if ms_label.get_rect(topleft=(30, 96)).collidepoint(mx, my):
                    cost = costs.get("unlock_main_switch", 2)
                    if store.profile.currency >= cost:
                        store.profile.currency -= cost
                        store.profile.main_switch_unlocked = True
                        store.save()

        if tab == 'shop':
            screen.blit(small.render("Sub-Weapons (click to unlock)", True, (220, 220, 220)), (30, 150))
            for i, key in enumerate(subs):
                rect = list_rect(i)
                unlocked = key in (store.profile.unlocked_subs or [])
                color = (255, 255, 180) if rect.collidepoint(mx, my) else (200, 200, 200)
                cost = costs.get(key, 1)
                label = f"{key} — {'Unlocked' if unlocked else f'Cost {cost}'}"
                pygame.draw.rect(screen, (40, 40, 50), rect)
                pygame.draw.rect(screen, (90, 90, 110), rect, 1)
                screen.blit(small.render(label, True, color), (rect.x + 6, rect.y + 2))
        elif tab == 'achievements':
            screen.blit(small.render("Achievements", True, (220, 220, 220)), (30, 150))
            y = 176
            defs = content.achievements or {}
            got = store.profile.achievements or {}
            for key, meta in defs.items():
                name = meta.get('name', key)
                desc = meta.get('description', '')
                ok = got.get(key, False)
                color = (180, 255, 180) if ok else (180, 180, 180)
                screen.blit(small.render(f"{name} {'(Done)' if ok else ''}", True, color), (30, y))
                y += 20
                screen.blit(small.render(desc, True, (200, 200, 200)), (40, y))
                y += 20
            # Totals
            totals = f"Totals — Kills {getattr(store.profile,'total_kills',0)}, Time {int(getattr(store.profile,'total_time',0))}s, Score {int(getattr(store.profile,'total_score',0))}"
            screen.blit(small.render(totals, True, (220,220,220)), (30, y+10))
        elif tab == 'save':
            screen.blit(small.render("Save & Profile", True, (220, 220, 220)), (30, 150))
            reset_rect = pygame.Rect(30, 180, 200, 28)
            pygame.draw.rect(screen, (100, 60, 60), reset_rect)
            pygame.draw.rect(screen, (200, 120, 120), reset_rect, 2)
            screen.blit(small.render("Reset Profile", True, (255, 230, 230)), (reset_rect.x + 20, reset_rect.y + 4))

        # Right pane: Unlocked details
        rx = 440
        screen.blit(small.render("Unlocked Subs:", True, (220, 220, 220)), (rx, 78))
        uy = 96
        for key in (store.profile.unlocked_subs or []):
            screen.blit(small.render(f"- {key}", True, (220, 220, 220)), (rx, uy))
            uy += 20

        # Footer
        screen.blit(small.render("Press S to start run", True, (200, 200, 255)), (30, settings.window.height - 36))

        pygame.display.flip()
