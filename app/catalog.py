"""De vaste lijst met bordonderdelen, verdeeld over 4 fases.

Gebruikers kiezen alleen een sleutel uit deze lijst; vrije tekst wordt nergens opgeslagen.
De namen zijn voorlopige plaatshouders tot de echte fases en onderdelen van het bord bekend zijn.
Wijzig nooit een bestaande sleutel: opgeslagen acties verwijzen ernaar.
"""

from dataclasses import dataclass

PHASE_NUMBERS = (1, 2, 3, 4)
PHASE_LABELS: dict[int, str] = {number: f"Fase {number}" for number in PHASE_NUMBERS}
COMPONENTS_PER_PHASE = 3


@dataclass(frozen=True)
class Component:
    key: str
    phase: int
    label: str


COMPONENTS: tuple[Component, ...] = tuple(
    Component(key=f"p{phase}c{number}", phase=phase, label=f"Onderdeel {phase}.{number}")
    for phase in PHASE_NUMBERS
    for number in range(1, COMPONENTS_PER_PHASE + 1)
)

_BY_KEY: dict[str, Component] = {component.key: component for component in COMPONENTS}


def get_component(key: str) -> Component | None:
    return _BY_KEY.get(key)


def components_in_phase(phase: int) -> list[Component]:
    return [component for component in COMPONENTS if component.phase == phase]
