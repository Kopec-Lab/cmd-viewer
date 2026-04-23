from __future__ import annotations

import re

from cmd_viewer.colors import LIPID_RESNAMES

WATER_RESNAMES = (
    "SOL",
    "HOH",
    "WAT",
    "TIP3",
    "TIP4",
    "TIP5",
    "SPC",
    "SPCE",
)

TOKEN_ALIASES = {
    "atomname": "name",
}


def normalize_selection(selection: str) -> str:
    normalized = selection.strip() or "all"
    for source, target in TOKEN_ALIASES.items():
        normalized = re.sub(rf"\b{re.escape(source)}\b", target, normalized)
    normalized = re.sub(r"\blipids\b", _lipids_selection(), normalized)
    return normalized


def build_selection(selection: str, show_water: bool) -> str:
    user_selection = normalize_selection(selection)
    if show_water:
        return user_selection

    water_terms = " or ".join(f"resname {resname}" for resname in WATER_RESNAMES)
    water_filter = f"not ({water_terms})"
    if user_selection == "all":
        return water_filter
    return f"({user_selection}) and ({water_filter})"


def _lipids_selection() -> str:
    lipid_terms = " or ".join(f"resname {resname}" for resname in sorted(LIPID_RESNAMES))
    return f"({lipid_terms})"
