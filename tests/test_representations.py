import numpy as np

from cmd_viewer.colors import visual_for_atom
from cmd_viewer.representations import build_frame_payload


def test_trace_payload_uses_ca_and_builds_backbone_lines() -> None:
    positions = np.array(
        [
            [0.0, 0.0, 0.0],
            [0.1, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.1, 0.0, 0.0],
            [2.0, 0.0, 0.0],
            [2.1, 0.0, 0.0],
        ]
    )
    payload = build_frame_payload(
        view_mode="trace",
        positions=positions,
        resnames=["ALA", "ALA", "GLY", "GLY", "SER", "SER"],
        elements=["C", "N", "C", "N", "C", "N"],
        atom_names=["N", "CA", "N", "CA", "N", "CA"],
        resids=[1, 1, 2, 2, 3, 3],
        center=positions.mean(axis=0, keepdims=True),
        box_corners=None,
        max_points=100,
        width=80,
        height=24,
    )
    assert len(payload.point_positions) == 3
    assert payload.point_chars == ["o", "o", "o"]
    assert len(payload.line_starts) == 2


def test_coarse_payload_collapses_atoms_per_residue() -> None:
    positions = np.array(
        [
            [0.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],
            [10.0, 0.0, 0.0],
            [12.0, 0.0, 0.0],
        ]
    )
    payload = build_frame_payload(
        view_mode="coarse",
        positions=positions,
        resnames=["POPC", "POPC", "LIG", "LIG"],
        elements=["C", "O", "C", "N"],
        atom_names=["C1", "P", "C1", "N1"],
        resids=[1, 1, 2, 2],
        center=positions.mean(axis=0, keepdims=True),
        box_corners=None,
        max_points=100,
        width=80,
        height=24,
    )
    assert len(payload.point_positions) == 2
    assert payload.point_chars == ["O", "D"]


def test_coarse_payload_uses_trace_only_for_protein() -> None:
    positions = np.array(
        [
            [0.0, 0.0, 0.0],
            [0.2, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.2, 0.0, 0.0],
        ]
    )
    payload = build_frame_payload(
        view_mode="coarse",
        positions=positions,
        resnames=["ALA", "ALA", "GLY", "GLY"],
        elements=["N", "C", "N", "C"],
        atom_names=["N", "CA", "N", "CA"],
        resids=[1, 1, 2, 2],
        center=positions.mean(axis=0, keepdims=True),
        box_corners=None,
        max_points=100,
        width=80,
        height=24,
    )
    assert len(payload.point_positions) == 0
    assert len(payload.line_starts) == 1


def test_cartoon_payload_marks_helix_like_segments_and_keeps_non_protein_markers() -> None:
    positions = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 2.0, 0.0],
            [10.0, 0.0, 0.0],
            [12.0, 0.0, 0.0],
        ]
    )
    payload = build_frame_payload(
        view_mode="cartoon",
        positions=positions,
        resnames=["ALA", "GLY", "SER", "THR", "VAL", "POPC", "POPC"],
        elements=["C", "C", "C", "C", "C", "P", "O"],
        atom_names=["CA", "CA", "CA", "CA", "CA", "P", "O1"],
        resids=[1, 2, 3, 4, 5, 6, 6],
        center=positions.mean(axis=0, keepdims=True),
        box_corners=None,
        max_points=100,
        width=80,
        height=24,
    )
    assert payload.point_chars == ["o", "o", "o", "o", "o", "O"]
    assert payload.line_chars == ["helix", "helix", "helix", "helix"]


def test_cartoon_payload_marks_sheet_like_segments() -> None:
    positions = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],
            [3.0, 0.0, 0.0],
        ]
    )
    payload = build_frame_payload(
        view_mode="cartoon",
        positions=positions,
        resnames=["ALA", "GLY", "SER", "THR"],
        elements=["C", "C", "C", "C"],
        atom_names=["CA", "CA", "CA", "CA"],
        resids=[1, 2, 3, 4],
        center=positions.mean(axis=0, keepdims=True),
        box_corners=None,
        max_points=100,
        width=80,
        height=24,
    )
    assert payload.line_chars == ["sheet", "sheet", "sheet"]


def test_ion_colors_follow_type_specific_mapping() -> None:
    assert visual_for_atom("class", "K", "K").color_id != visual_for_atom("class", "CL", "CL").color_id
    assert visual_for_atom("class", "NA", "NA").char == "*"


def test_resid_color_mode_cycles_by_residue_id_and_keeps_default_ion_size() -> None:
    ion_one = visual_for_atom("resid", "K", "K", 1)
    ion_two = visual_for_atom("resid", "K", "K", 2)
    assert ion_one.color_id != ion_two.color_id
    assert ion_one.footprint == 0
