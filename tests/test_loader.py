import warnings
from pathlib import Path

import MDAnalysis as mda
import numpy as np

from cmd_viewer.loader import load_system


def test_load_system_supports_dcd_trajectories(tmp_path: Path) -> None:
    universe = mda.Universe.empty(
        2,
        n_residues=1,
        atom_resindex=[0, 0],
        trajectory=True,
    )
    universe.add_TopologyAttr("names", ["C1", "C2"])
    universe.add_TopologyAttr("types", ["C", "C"])
    universe.add_TopologyAttr("resnames", ["MOL"])
    universe.add_TopologyAttr("resids", [1])
    universe.add_TopologyAttr("segids", ["SYS"])
    universe.add_TopologyAttr("elements", ["C", "C"])
    universe.add_TopologyAttr("chainIDs", ["A", "A"])
    universe.add_TopologyAttr("altLocs", ["", ""])
    universe.add_TopologyAttr("occupancies", [1.0, 1.0])
    universe.add_TopologyAttr("tempfactors", [0.0, 0.0])
    universe.add_TopologyAttr("record_types", ["ATOM", "ATOM"])
    universe.dimensions = np.array([20.0, 20.0, 20.0, 90.0, 90.0, 90.0], dtype=float)

    structure_path = tmp_path / "system.pdb"
    trajectory_path = tmp_path / "traj.dcd"
    universe.atoms.positions = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
        ],
        dtype=float,
    )
    universe.atoms.write(structure_path)

    with mda.coordinates.DCD.DCDWriter(str(trajectory_path), universe.atoms.n_atoms) as writer:
        for shift in (0.0, 1.5):
            universe.atoms.positions = np.array(
                [
                    [shift, 0.0, 0.0],
                    [shift + 1.0, 0.0, 0.0],
                ],
                dtype=float,
            )
            writer.write(universe.atoms)

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="DCDReader currently makes independent timesteps",
            category=DeprecationWarning,
        )
        loaded = load_system(
            str(structure_path),
            str(trajectory_path),
            selection="all",
            show_water=True,
        )

    assert loaded.frame_count == 2
    loaded.universe.trajectory[1]
    np.testing.assert_allclose(
        loaded.atoms.positions,
        np.array(
            [
                [1.5, 0.0, 0.0],
                [2.5, 0.0, 0.0],
            ],
            dtype=float,
        ),
    )
