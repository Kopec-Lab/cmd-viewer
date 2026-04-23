from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

import numpy as np

from cmd_viewer.colors import LIPID_RESNAMES
from cmd_viewer.selection import normalize_selection


DEFAULT_SMOOTH_SELECTION = "protein or " + " or ".join(
    f"resname {resname}" for resname in sorted(LIPID_RESNAMES)
)


@dataclass(slots=True)
class SmoothingConfig:
    enabled: bool
    window: int
    selection: str
    smoothed_atom_count: int


class TrajectorySmoother:
    def __init__(
        self,
        universe,
        atoms,
        window: int,
        smooth_selection: str | None,
    ) -> None:
        self.universe = universe
        self.atoms = atoms
        self.window = max(window, 0)
        normalized_selection = normalize_selection(smooth_selection or DEFAULT_SMOOTH_SELECTION)
        self.selection = normalized_selection
        self.frame_count = len(universe.trajectory)
        self._subset_cache: OrderedDict[int, np.ndarray] = OrderedDict()

        if self.window <= 1:
            self.local_indices = np.empty(0, dtype=int)
            self.config = SmoothingConfig(
                enabled=False,
                window=self.window,
                selection=normalized_selection,
                smoothed_atom_count=0,
            )
            return

        smooth_atoms = atoms.select_atoms(normalized_selection)
        if smooth_atoms.n_atoms == 0:
            self.local_indices = np.empty(0, dtype=int)
            self.config = SmoothingConfig(
                enabled=False,
                window=self.window,
                selection=normalized_selection,
                smoothed_atom_count=0,
            )
            return

        atom_lookup = {atom_index: local_index for local_index, atom_index in enumerate(atoms.ix)}
        self.local_indices = np.array(
            [atom_lookup[atom_index] for atom_index in smooth_atoms.ix],
            dtype=int,
        )
        self._smooth_atoms = smooth_atoms
        self._cache_limit = max(self.window * 4, 16)
        self.config = SmoothingConfig(
            enabled=True,
            window=self.window,
            selection=normalized_selection,
            smoothed_atom_count=len(self.local_indices),
        )

    def smooth_positions(
        self,
        frame_index: int,
        current_positions: np.ndarray,
    ) -> np.ndarray:
        if not self.config.enabled:
            return current_positions

        smoothed_positions = current_positions.copy()
        averaged_subset = np.zeros((len(self.local_indices), 3), dtype=float)
        start, end = _window_bounds(frame_index, self.frame_count, self.window)
        for window_frame in range(start, end):
            if window_frame == frame_index:
                subset_positions = current_positions[self.local_indices]
            else:
                subset_positions = self._subset_positions_for_frame(window_frame)
            averaged_subset += subset_positions
        averaged_subset /= max(end - start, 1)
        smoothed_positions[self.local_indices] = averaged_subset
        self.universe.trajectory[frame_index]
        return smoothed_positions

    def _subset_positions_for_frame(self, frame_index: int) -> np.ndarray:
        cached = self._subset_cache.get(frame_index)
        if cached is not None:
            self._subset_cache.move_to_end(frame_index)
            return cached

        self.universe.trajectory[frame_index]
        subset_positions = self._smooth_atoms.positions.copy()
        self._subset_cache[frame_index] = subset_positions
        if len(self._subset_cache) > self._cache_limit:
            self._subset_cache.popitem(last=False)
        return subset_positions


def _window_bounds(frame_index: int, frame_count: int, window: int) -> tuple[int, int]:
    window = max(window, 1)
    half_window = window // 2
    start = max(frame_index - half_window, 0)
    end = min(start + window, frame_count)
    start = max(end - window, 0)
    return start, end
