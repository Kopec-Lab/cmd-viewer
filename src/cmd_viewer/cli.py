from __future__ import annotations

import argparse

from cmd_viewer import __version__
from cmd_viewer.app import run_viewer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cmd",
        description="Terminal molecular dynamics viewer for structure and trajectory files.",
    )
    parser.add_argument("structure", help="Structure/topology file (.gro, .pdb, ...).")
    parser.add_argument(
        "trajectory",
        nargs="?",
        help="Optional trajectory file (.xtc, .trr, .dcd, ...).",
    )
    parser.add_argument(
        "--selection",
        default="all",
        help="Atom selection expression. VMD-like habits are normalized where possible.",
    )
    parser.add_argument(
        "--show-water",
        action="store_true",
        help="Include water in the visible selection.",
    )
    parser.add_argument(
        "--start-frame",
        type=int,
        default=0,
        help="Frame index to open initially.",
    )
    parser.add_argument(
        "--stride",
        type=int,
        default=1,
        help="Display every Nth trajectory frame.",
    )
    parser.add_argument(
        "--max-points",
        type=int,
        default=40000,
        help="Maximum number of atoms projected per frame before downsampling.",
    )
    parser.add_argument(
        "--color-mode",
        choices=("class", "element", "resid"),
        default="class",
        help="Color atoms by biomolecular class, element, or residue id.",
    )
    parser.add_argument(
        "--view-mode",
        choices=("points", "trace", "coarse", "cartoon"),
        default="points",
        help="Visualization mode to use at startup.",
    )
    parser.add_argument(
        "--smooth",
        type=int,
        default=0,
        metavar="N",
        help="Smooth selected atom motion over a centered window of N frames.",
    )
    parser.add_argument(
        "--smoothres",
        default=None,
        help="Selection expression for which atoms/residues to smooth. Defaults to protein and lipids.",
    )
    parser.add_argument(
        "--near-water",
        type=float,
        default=0.0,
        metavar="ANGSTROM",
        help="Show water oxygens within the given cutoff of a target selection, updated every frame.",
    )
    parser.add_argument(
        "--near-water-target",
        default="protein",
        help="Target selection used with --near-water. Defaults to protein.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    run_viewer(args)
    return 0
