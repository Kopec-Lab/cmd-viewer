from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cmd_viewer.selection import WATER_RESNAMES, normalize_selection


WATER_OXYGEN_NAMES = ("O", "OW", "OH2", "OT")
POCKET_WATER_COLOR_ID = 8


@dataclass(slots=True)
class PocketWaterConfig:
    enabled: bool
    cutoff: float
    target_selection: str


class PocketWaterOverlay:
    def __init__(
        self,
        universe,
        cutoff: float,
        target_selection: str | None,
    ) -> None:
        normalized_target = normalize_selection(target_selection or "protein")
        self.config = PocketWaterConfig(
            enabled=cutoff > 0.0,
            cutoff=max(cutoff, 0.0),
            target_selection=normalized_target,
        )
        self._overlay_atoms = None
        if not self.config.enabled:
            return

        water_terms = " or ".join(f"resname {resname}" for resname in WATER_RESNAMES)
        oxygen_terms = " or ".join(f"name {name}" for name in WATER_OXYGEN_NAMES)
        selection = (
            f"({water_terms}) and ({oxygen_terms}) and "
            f"around {self.config.cutoff:.3f} ({normalized_target})"
        )
        self._overlay_atoms = universe.select_atoms(selection, updating=True)

    def positions(self) -> np.ndarray:
        if not self.config.enabled or self._overlay_atoms is None:
            return np.empty((0, 3), dtype=float)
        return self._overlay_atoms.positions.copy()
