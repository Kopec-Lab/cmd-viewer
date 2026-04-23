from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from cmd_viewer.selection import build_selection

if TYPE_CHECKING:
    import MDAnalysis as mda


@dataclass(slots=True)
class LoadedSystem:
    universe: "mda.Universe"
    atoms: "mda.core.groups.AtomGroup"
    selection: str
    structure_path: Path
    trajectory_path: Path | None

    @property
    def frame_count(self) -> int:
        return len(self.universe.trajectory)


def load_system(
    structure_path: str,
    trajectory_path: str | None,
    selection: str,
    show_water: bool,
) -> LoadedSystem:
    try:
        import MDAnalysis as mda
    except ImportError as exc:
        raise RuntimeError(
            "MDAnalysis is required to load structures and trajectories. "
            "Install the package dependencies first."
        ) from exc

    structure = Path(structure_path)
    trajectory = Path(trajectory_path) if trajectory_path else None
    universe = (
        mda.Universe(str(structure), str(trajectory))
        if trajectory
        else mda.Universe(str(structure))
    )
    final_selection = build_selection(selection, show_water)
    atoms = universe.select_atoms(final_selection)
    if atoms.n_atoms == 0:
        raise ValueError(
            f"Selection matched zero atoms: {final_selection}"
        )

    return LoadedSystem(
        universe=universe,
        atoms=atoms,
        selection=final_selection,
        structure_path=structure,
        trajectory_path=trajectory,
    )
