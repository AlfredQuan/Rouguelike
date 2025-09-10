from __future__ import annotations

# This shim ensures we have an `esper`-like API even if a conflicting
# package named `esper` is installed without World/Processor.

try:
    import esper as _esper  # type: ignore
    if hasattr(_esper, "World") and hasattr(_esper, "Processor"):
        esper = _esper  # re-export real library
    else:
        raise ImportError("esper module lacks World/Processor")
except Exception:  # pragma: no cover - fallback path
    # Minimal drop-in ECS used by this project
    class Processor:
        def __init__(self) -> None:
            self.world: World | None = None

        def process(self, dt: float) -> None:  # override in subclasses
            pass

    class World:
        def __init__(self) -> None:
            self._next_eid = 1
            self._entities: set[int] = set()
            self._components: dict[type, dict[int, object]] = {}
            self._processors: list[tuple[int, Processor]] = []

        # Entity lifecycle
        def create_entity(self) -> int:
            eid = self._next_eid
            self._next_eid += 1
            self._entities.add(eid)
            return eid

        def delete_entity(self, eid: int) -> None:
            for mapping in self._components.values():
                mapping.pop(eid, None)
            self._entities.discard(eid)

        # Components
        def add_component(self, eid: int, component: object) -> None:
            t = type(component)
            self._components.setdefault(t, {})[eid] = component

        def get_component(self, comp_type: type):
            mapping = self._components.get(comp_type, {})
            return list(mapping.items())

        def component_for_entity(self, eid: int, comp_type: type):
            return self._components.get(comp_type, {}).get(eid)

        def get_components(self, *comp_types: type):
            if not comp_types:
                return []
            sets = [set(self._components.get(t, {}).keys()) for t in comp_types]
            common = set.intersection(*sets) if sets else set()
            out = []
            for eid in common:
                out.append((eid, tuple(self._components[t][eid] for t in comp_types)))
            return out

        # Processors
        def add_processor(self, processor: Processor, priority: int = 0) -> None:
            processor.world = self
            self._processors.append((priority, processor))
            self._processors.sort(key=lambda x: x[0], reverse=True)

        def process(self, dt: float) -> None:
            for _, p in self._processors:
                p.process(dt)

    # Expose as a module-like object for import symmetry
    class _ShimModule:
        World = World
        Processor = Processor

    esper = _ShimModule()  # type: ignore
