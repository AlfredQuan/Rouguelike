Roguelike Survivor (Vampire Survivors-like) — Python Scaffold

Overview
- Tech: Python, pygame, esper (ECS), PyYAML
- Goals: Clear constants/config, easy content modding, extendable systems, meta-progression persistence.

Structure
- `main.py`: Entry point, game loop bootstrap.
- `roguelike/`: Game package with ECS components, systems, factories, services.
- `config/settings.yaml`: Tunable constants for window, gameplay, balancing.
- `data/*.yaml`: Content definitions for characters, enemies, weapons, pickups, cards.
  - `data/weapons_main.yaml`: Main weapons (projectile, burst, etc.).
  - `data/weapons_sub.yaml`: Sub weapons (orbitals, support bursts, etc.).
- `save/profile.json`: Meta-progression save (auto-created).
- `assets/`: Placeholder for images, sounds, fonts.

Setup
1) Python 3.10+
2) Install deps: `pip install -r requirements.txt`
3) Run: `python main.py`

Extending Content
- Add or tweak YAML in `data/` — no code changes required for basic stats.
- To add new behavior, create new Systems/Components and wire them in `roguelike/game.py`.

Weapons
- Main weapons (multiple): defined in `data/weapons_main.yaml` with `behavior`, `fire_rate`, `damage`, `speed`, `lifetime`, optional `count`, `spread_deg`.
- Sub weapons (multiple): defined in `data/weapons_sub.yaml` with `behavior` like `orbital` (uses `count`, `radius`, `angular_speed_deg`, `damage`) or `radial_burst`.
- Characters can equip defaults via `data/characters.yaml` under `starting_main`, `starting_sub`.

Meta-Progression
- Stored in `save/profile.json`. Currency, unlocks, and upgrades persist across runs.

Notes
- This is a minimal, clean scaffold to iterate quickly. Replace placeholder art and expand systems as needed.
