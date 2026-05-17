from __future__ import annotations

from dataclasses import dataclass


COLOR_IDS = {
    "default": 0,
    "protein": 1,
    "lipid": 2,
    "ion": 3,
    "water": 4,
    "ligand": 5,
    "carbon": 6,
    "nitrogen": 7,
    "oxygen": 8,
    "potassium": 9,
    "chloride": 10,
    "sodium": 11,
    "calcium": 12,
    "magnesium": 13,
    "zinc": 14,
}

LIPID_RESNAMES = {
    "POPC",
    "POPE",
    "POPG",
    "POPS",
    "DPPC",
    "DPPE",
    "DPPG",
    "DPPS",
    "CHOL",
    "DOPC",
    "DOPE",
    "DOPG",
    "DOPS",
    "DLPC",
    "DLPE",
    "DSPC",
    "DSPE",
    "SOPC",
    "SOPE",
}

PROTEIN_RESNAMES = {
    "ACE",
    "ALA",
    "ARG",
    "ASN",
    "ASP",
    "ASH",
    "CYS",
    "CYX",
    "CYM",
    "GLN",
    "GLU",
    "GLH",
    "GLY",
    "HIS",
    "HID",
    "HIE",
    "HIP",
    "HSD",
    "HSE",
    "HSP",
    "ILE",
    "LEU",
    "LYS",
    "LYN",
    "MET",
    "NME",
    "PHE",
    "PRO",
    "SER",
    "THR",
    "TRP",
    "TYR",
    "VAL",
}

NUCLEIC_RESNAMES = {
    "A",
    "C",
    "G",
    "U",
    "T",
    "DA",
    "DC",
    "DG",
    "DT",
    "RA",
    "RC",
    "RG",
    "RU",
}

ION_NAMES = {
    "NA",
    "K",
    "CL",
    "CA",
    "MG",
    "ZN",
}

ION_COLOR_IDS = {
    "K": COLOR_IDS["potassium"],
    "CL": COLOR_IDS["chloride"],
    "NA": COLOR_IDS["sodium"],
    "CA": COLOR_IDS["calcium"],
    "MG": COLOR_IDS["magnesium"],
    "ZN": COLOR_IDS["zinc"],
}

WATER_RESNAMES = {
    "SOL",
    "HOH",
    "WAT",
    "TIP3",
    "TIP4",
    "TIP5",
    "SPC",
    "SPCE",
}


@dataclass(frozen=True, slots=True)
class AtomVisual:
    char: str
    color_id: int
    footprint: int = 0


RESID_COLOR_CYCLE = (
    COLOR_IDS["protein"],
    COLOR_IDS["lipid"],
    COLOR_IDS["ligand"],
    COLOR_IDS["nitrogen"],
    COLOR_IDS["oxygen"],
    COLOR_IDS["potassium"],
    COLOR_IDS["chloride"],
    COLOR_IDS["sodium"],
    COLOR_IDS["calcium"],
    COLOR_IDS["magnesium"],
    COLOR_IDS["zinc"],
    COLOR_IDS["carbon"],
)


def biomolecular_class(resname: str, element: str) -> str:
    normalized_resname = (resname or "").upper()
    normalized_element = (element or "").upper()
    if normalized_resname in WATER_RESNAMES:
        return "water"
    if normalized_resname in LIPID_RESNAMES:
        return "lipid"
    if normalized_element in ION_NAMES:
        return "ion"
    if normalized_resname in PROTEIN_RESNAMES or normalized_resname in NUCLEIC_RESNAMES:
        return "protein"
    return "ligand"


def visual_for_atom(
    color_mode: str,
    resname: str,
    element: str,
    resid: int | None = None,
) -> AtomVisual:
    normalized_element = (element or "C").upper()
    atom_class = biomolecular_class(resname, normalized_element)
    footprint = 0
    if color_mode == "element":
        if normalized_element == "O":
            return AtomVisual(char="o", color_id=COLOR_IDS["oxygen"], footprint=footprint)
        if normalized_element == "N":
            return AtomVisual(char="n", color_id=COLOR_IDS["nitrogen"], footprint=footprint)
        return AtomVisual(char=".", color_id=COLOR_IDS["carbon"], footprint=footprint)

    char_map = {
        "protein": "@",
        "lipid": "=",
        "ion": "*",
        "water": ".",
        "ligand": "+",
    }
    if color_mode == "resid":
        color_id = (
            COLOR_IDS.get(atom_class, 0)
            if resid is None
            else RESID_COLOR_CYCLE[abs(int(resid)) % len(RESID_COLOR_CYCLE)]
        )
        return AtomVisual(
            char=char_map.get(atom_class, "."),
            color_id=color_id,
            footprint=footprint,
        )
    if atom_class == "ion":
        return AtomVisual(
            char=char_map["ion"],
            color_id=ION_COLOR_IDS.get(normalized_element, COLOR_IDS["ion"]),
            footprint=footprint,
        )
    return AtomVisual(
        char=char_map.get(atom_class, "."),
        color_id=COLOR_IDS.get(atom_class, 0),
        footprint=footprint,
    )
