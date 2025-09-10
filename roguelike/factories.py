from __future__ import annotations

from typing import Tuple, List, Optional

from .esper_compat import esper

from .content import Content
from .ecs_components import (
    Collider,
    Enemy,
    Experience,
    Faction,
    Health,
    Loadout,
    Pickup,
    Player,
    Position,
    Sprite,
    Speed,
    Velocity,
    WeaponInstance,
)


def create_player(world: esper.World, content: Content, key: str, pos: Tuple[float, float], main_key: Optional[str] = None) -> int:
    ch = content.character(key)
    # Starting main: single weapon (either from meta selection or fallback)
    start_main_key: str = main_key or ch.get("starting_main", [ch.get("starting_weapon", "basic_bolt")])[0]
    start_sub: List[str] = list(ch.get("starting_sub", []))
    e = world.create_entity()
    world.add_component(e, Position(float(pos[0]), float(pos[1])))
    world.add_component(e, Velocity(0.0, 0.0))
    world.add_component(e, Player())
    world.add_component(e, Faction("player"))
    world.add_component(e, Collider(radius=int(ch.get("radius", 14))))
    world.add_component(e, Sprite(tuple(ch.get("color", (60, 200, 255))), int(ch.get("radius", 14))))
    max_hp = int(ch.get("max_health", 100))
    world.add_component(e, Health(current=max_hp, max_hp=max_hp))
    world.add_component(e, Experience())
    move_speed = float(ch.get("move_speed", 180.0))
    world.add_component(e, Speed(base=move_speed))
    # Loadout with single main and multiple sub weapon instances
    main_inst: Optional[WeaponInstance] = None
    wd = content.weapon_main(start_main_key) or content.weapon(start_main_key)
    if wd:
        main_inst = WeaponInstance(
            key=start_main_key,
            behavior=str(wd.get("behavior", "projectile")),
            fire_rate=float(wd.get("fire_rate", 2.0)),
            cooldown=0.0,
            damage=int(wd.get("damage", 10)),
            speed=float(wd.get("speed", 350.0)),
            lifetime=float(wd.get("lifetime", 1.2)),
            count=int(wd.get("count", 1)),
            spread_deg=float(wd.get("spread_deg", 0.0)),
            pierce=int(wd.get("pierce", 0)),
        )

    sub_instances: List[WeaponInstance] = []
    for wk in start_sub:
        wd = content.weapon_sub(wk)
        if not wd:
            continue
        inst = WeaponInstance(
            key=wk,
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
        sub_instances.append(inst)

    world.add_component(e, Loadout(main=main_inst, sub=sub_instances))
    return e
