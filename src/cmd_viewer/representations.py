from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from cmd_viewer.colors import COLOR_IDS, biomolecular_class


TRACE_PRIORITY = {
    "CA": 0,
    "BB": 1,
    "P": 2,
    "C4'": 3,
    "C3'": 4,
}

PROTEIN_CAP_TRACE_PRIORITY = {
    "ACE": {
        "C": 0,
        "CH3": 1,
    },
    "NME": {
        "N": 0,
        "CH3": 1,
    },
}

COARSE_CHAR_MAP = {
    "lipid": "O",
    "ion": "*",
    "water": ".",
    "ligand": "D",
}

HELIX_MIN_RUN = 3
SHEET_MIN_RUN = 2


@dataclass(slots=True)
class FramePayload:
    point_positions: np.ndarray
    point_resnames: list[str]
    point_elements: list[str]
    point_resids: list[int]
    point_chars: list[str] | None
    line_starts: np.ndarray
    line_ends: np.ndarray
    line_chars: list[str]
    line_color_ids: list[int]
    center: np.ndarray
    box_corners: np.ndarray | None
    atom_count: int
    displayed_count: int
    view_mode: str
    overlay_positions: np.ndarray = field(default_factory=lambda: np.empty((0, 3), dtype=float))
    overlay_chars: list[str] = field(default_factory=list)
    overlay_color_ids: list[int] = field(default_factory=list)


def build_frame_payload(
    view_mode: str,
    positions: np.ndarray,
    resnames: list[str],
    elements: list[str],
    atom_names: list[str],
    resids: list[int],
    center: np.ndarray,
    box_corners: np.ndarray | None,
    max_points: int,
    width: int,
    height: int,
) -> FramePayload:
    if view_mode == "trace":
        payload = _build_trace_payload(
            positions=positions,
            resnames=resnames,
            elements=elements,
            atom_names=atom_names,
            resids=resids,
            center=center,
            box_corners=box_corners,
        )
    elif view_mode == "cartoon":
        payload = _build_cartoon_payload(
            positions=positions,
            resnames=resnames,
            elements=elements,
            atom_names=atom_names,
            resids=resids,
            center=center,
            box_corners=box_corners,
        )
    elif view_mode == "coarse":
        payload = _build_coarse_payload(
            positions=positions,
            resnames=resnames,
            elements=elements,
            atom_names=atom_names,
            resids=resids,
            center=center,
            box_corners=box_corners,
        )
    else:
        payload = _build_points_payload(
            positions=positions,
            resnames=resnames,
            elements=elements,
            resids=resids,
            center=center,
            box_corners=box_corners,
        )

    return _downsample_payload(
        payload=payload,
        max_points=max_points,
        width=width,
        height=height,
    )


def _build_points_payload(
    positions: np.ndarray,
    resnames: list[str],
    elements: list[str],
    resids: list[int],
    center: np.ndarray,
    box_corners: np.ndarray | None,
) -> FramePayload:
    atom_count = len(positions)
    return FramePayload(
        point_positions=positions,
        point_resnames=resnames,
        point_elements=elements,
        point_resids=resids,
        point_chars=None,
        line_starts=np.empty((0, 3), dtype=float),
        line_ends=np.empty((0, 3), dtype=float),
        line_chars=[],
        line_color_ids=[],
        center=center,
        box_corners=box_corners,
        atom_count=atom_count,
        displayed_count=atom_count,
        view_mode="points",
    )


def _build_trace_payload(
    positions: np.ndarray,
    resnames: list[str],
    elements: list[str],
    atom_names: list[str],
    resids: list[int],
    center: np.ndarray,
    box_corners: np.ndarray | None,
) -> FramePayload:
    residue_blocks = _residue_blocks(resids, resnames)
    trace_points: list[np.ndarray] = []
    trace_resnames: list[str] = []
    trace_elements: list[str] = []
    trace_resids: list[int] = []
    trace_chars: list[str] = []
    line_starts: list[np.ndarray] = []
    line_ends: list[np.ndarray] = []
    line_chars: list[str] = []
    line_color_ids: list[int] = []

    previous_trace: tuple[np.ndarray, int, str] | None = None
    for start, end in residue_blocks:
        trace_index = _select_trace_index(atom_names, resnames, start, end)
        if trace_index is None:
            continue
        point = positions[trace_index]
        resname = resnames[trace_index]
        element = elements[trace_index]
        trace_points.append(point)
        trace_resnames.append(resname)
        trace_elements.append(element)
        trace_resids.append(resids[trace_index])
        trace_chars.append("o")

        residue_class = biomolecular_class(resname, element)
        if previous_trace is not None:
            previous_point, previous_resid, previous_class = previous_trace
            current_resid = resids[trace_index]
            if (
                residue_class == previous_class == "protein"
                and abs(current_resid - previous_resid) <= 1
            ):
                line_starts.append(previous_point)
                line_ends.append(point)
                line_chars.append("-")
                line_color_ids.append(COLOR_IDS["protein"])
        previous_trace = (point, resids[trace_index], residue_class)

    if not trace_points:
        return _build_points_payload(positions, resnames, elements, resids, center, box_corners)

    return FramePayload(
        point_positions=np.asarray(trace_points, dtype=float),
        point_resnames=trace_resnames,
        point_elements=trace_elements,
        point_resids=trace_resids,
        point_chars=trace_chars,
        line_starts=np.asarray(line_starts, dtype=float) if line_starts else np.empty((0, 3), dtype=float),
        line_ends=np.asarray(line_ends, dtype=float) if line_ends else np.empty((0, 3), dtype=float),
        line_chars=line_chars,
        line_color_ids=line_color_ids,
        center=center,
        box_corners=box_corners,
        atom_count=len(positions),
        displayed_count=len(trace_points) + len(line_starts),
        view_mode="trace",
    )


def _build_cartoon_payload(
    positions: np.ndarray,
    resnames: list[str],
    elements: list[str],
    atom_names: list[str],
    resids: list[int],
    center: np.ndarray,
    box_corners: np.ndarray | None,
) -> FramePayload:
    return _build_protein_path_payload(
        positions=positions,
        resnames=resnames,
        elements=elements,
        atom_names=atom_names,
        resids=resids,
        center=center,
        box_corners=box_corners,
        include_non_protein_points=True,
        protein_line_char="ss",
        view_mode="cartoon",
    )


def _build_coarse_payload(
    positions: np.ndarray,
    resnames: list[str],
    elements: list[str],
    atom_names: list[str],
    resids: list[int],
    center: np.ndarray,
    box_corners: np.ndarray | None,
) -> FramePayload:
    return _build_protein_path_payload(
        positions=positions,
        resnames=resnames,
        elements=elements,
        atom_names=atom_names,
        resids=resids,
        center=center,
        box_corners=box_corners,
        include_non_protein_points=True,
        protein_line_char="-",
        view_mode="coarse",
    )


def _build_protein_path_payload(
    positions: np.ndarray,
    resnames: list[str],
    elements: list[str],
    atom_names: list[str],
    resids: list[int],
    center: np.ndarray,
    box_corners: np.ndarray | None,
    include_non_protein_points: bool,
    protein_line_char: str,
    view_mode: str,
) -> FramePayload:
    residue_blocks = _residue_blocks(resids, resnames)
    coarse_points: list[np.ndarray] = []
    coarse_resnames: list[str] = []
    coarse_elements: list[str] = []
    coarse_resids: list[int] = []
    coarse_chars: list[str] = []
    line_starts: list[np.ndarray] = []
    line_ends: list[np.ndarray] = []
    line_chars: list[str] = []
    line_color_ids: list[int] = []
    protein_segment_points: list[np.ndarray] = []
    protein_segment_resids: list[int] = []
    protein_segment_resnames: list[str] = []
    protein_segment_elements: list[str] = []

    for start, end in residue_blocks:
        residue_positions = positions[start:end]
        residue_center = residue_positions.mean(axis=0)
        resname = resnames[start]
        element = elements[start]
        residue_class = biomolecular_class(resname, element)

        trace_index = _select_trace_index(atom_names, resnames, start, end)
        if residue_class == "protein":
            if trace_index is None:
                _append_protein_segment(
                    segment_points=protein_segment_points,
                    segment_resids=protein_segment_resids,
                    segment_resnames=protein_segment_resnames,
                    segment_elements=protein_segment_elements,
                    point_positions=coarse_points,
                    point_resnames=coarse_resnames,
                    point_elements=coarse_elements,
                    point_resids=coarse_resids,
                    point_chars=coarse_chars,
                    line_starts=line_starts,
                    line_ends=line_ends,
                    line_chars=line_chars,
                    line_color_ids=line_color_ids,
                    protein_line_char=protein_line_char,
                    view_mode=view_mode,
                )
                protein_segment_points = []
                protein_segment_resids = []
                protein_segment_resnames = []
                protein_segment_elements = []
                continue

            if protein_segment_resids and abs(resids[start] - protein_segment_resids[-1]) > 1:
                _append_protein_segment(
                    segment_points=protein_segment_points,
                    segment_resids=protein_segment_resids,
                    segment_resnames=protein_segment_resnames,
                    segment_elements=protein_segment_elements,
                    point_positions=coarse_points,
                    point_resnames=coarse_resnames,
                    point_elements=coarse_elements,
                    point_resids=coarse_resids,
                    point_chars=coarse_chars,
                    line_starts=line_starts,
                    line_ends=line_ends,
                    line_chars=line_chars,
                    line_color_ids=line_color_ids,
                    protein_line_char=protein_line_char,
                    view_mode=view_mode,
                )
                protein_segment_points = []
                protein_segment_resids = []
                protein_segment_resnames = []
                protein_segment_elements = []

            protein_segment_points.append(positions[trace_index])
            protein_segment_resids.append(resids[start])
            protein_segment_resnames.append(resname)
            protein_segment_elements.append(element)
            continue

        _append_protein_segment(
            segment_points=protein_segment_points,
            segment_resids=protein_segment_resids,
            segment_resnames=protein_segment_resnames,
            segment_elements=protein_segment_elements,
            point_positions=coarse_points,
            point_resnames=coarse_resnames,
            point_elements=coarse_elements,
            point_resids=coarse_resids,
            point_chars=coarse_chars,
            line_starts=line_starts,
            line_ends=line_ends,
            line_chars=line_chars,
            line_color_ids=line_color_ids,
            protein_line_char=protein_line_char,
            view_mode=view_mode,
        )
        protein_segment_points = []
        protein_segment_resids = []
        protein_segment_resnames = []
        protein_segment_elements = []

        if not include_non_protein_points:
            continue

        if residue_class == "lipid":
            coarse_index = _select_lipid_head_index(atom_names, start, end)
            coarse_point = positions[coarse_index] if coarse_index is not None else residue_center
        else:
            coarse_point = residue_center

        coarse_points.append(coarse_point)
        coarse_resnames.append(resname)
        coarse_elements.append(element)
        coarse_resids.append(resids[start])
        coarse_chars.append(COARSE_CHAR_MAP.get(residue_class, "D"))

    _append_protein_segment(
        segment_points=protein_segment_points,
        segment_resids=protein_segment_resids,
        segment_resnames=protein_segment_resnames,
        segment_elements=protein_segment_elements,
        point_positions=coarse_points,
        point_resnames=coarse_resnames,
        point_elements=coarse_elements,
        point_resids=coarse_resids,
        point_chars=coarse_chars,
        line_starts=line_starts,
        line_ends=line_ends,
        line_chars=line_chars,
        line_color_ids=line_color_ids,
        protein_line_char=protein_line_char,
        view_mode=view_mode,
    )

    return FramePayload(
        point_positions=np.asarray(coarse_points, dtype=float),
        point_resnames=coarse_resnames,
        point_elements=coarse_elements,
        point_resids=coarse_resids,
        point_chars=coarse_chars,
        line_starts=np.asarray(line_starts, dtype=float) if line_starts else np.empty((0, 3), dtype=float),
        line_ends=np.asarray(line_ends, dtype=float) if line_ends else np.empty((0, 3), dtype=float),
        line_chars=line_chars,
        line_color_ids=line_color_ids,
        center=center,
        box_corners=box_corners,
        atom_count=len(positions),
        displayed_count=len(coarse_points) + len(line_starts),
        view_mode=view_mode,
    )


def _downsample_payload(
    payload: FramePayload,
    max_points: int,
    width: int,
    height: int,
) -> FramePayload:
    screen_budget = max(width * max(height, 1) * 4, 1)
    target_count = min(max_points, screen_budget)
    point_count = len(payload.point_positions)
    if point_count <= target_count:
        return payload

    stride = math.ceil(point_count / target_count)
    sampled_slice = slice(None, None, stride)
    point_chars = payload.point_chars[sampled_slice] if payload.point_chars is not None else None
    return FramePayload(
        point_positions=payload.point_positions[sampled_slice],
        point_resnames=payload.point_resnames[sampled_slice],
        point_elements=payload.point_elements[sampled_slice],
        point_resids=payload.point_resids[sampled_slice],
        point_chars=point_chars,
        line_starts=payload.line_starts,
        line_ends=payload.line_ends,
        line_chars=payload.line_chars,
        line_color_ids=payload.line_color_ids,
        center=payload.center,
        box_corners=payload.box_corners,
        atom_count=payload.atom_count,
        displayed_count=len(payload.point_positions[sampled_slice]) + len(payload.line_starts),
        view_mode=payload.view_mode,
    )


def _residue_blocks(resids: list[int], resnames: list[str]) -> list[tuple[int, int]]:
    if not resids:
        return []
    blocks: list[tuple[int, int]] = []
    start = 0
    for index in range(1, len(resids)):
        if resids[index] != resids[index - 1] or resnames[index] != resnames[index - 1]:
            blocks.append((start, index))
            start = index
    blocks.append((start, len(resids)))
    return blocks


def _select_trace_index(
    atom_names: list[str],
    resnames: list[str],
    start: int,
    end: int,
) -> int | None:
    best_index: int | None = None
    best_priority = math.inf
    for index in range(start, end):
        priority = TRACE_PRIORITY.get(atom_names[index].upper())
        if priority is not None and priority < best_priority:
            best_index = index
            best_priority = priority
    if best_index is not None:
        return best_index

    residue_name = resnames[start].upper()
    cap_priority = PROTEIN_CAP_TRACE_PRIORITY.get(residue_name)
    if cap_priority is None:
        return None

    for index in range(start, end):
        priority = cap_priority.get(atom_names[index].upper())
        if priority is not None and priority < best_priority:
            best_index = index
            best_priority = priority
    return best_index


def _select_lipid_head_index(atom_names: list[str], start: int, end: int) -> int | None:
    preferred_exact = ("P", "N")
    for target in preferred_exact:
        for index in range(start, end):
            if atom_names[index].upper() == target:
                return index

    for index in range(start, end):
        atom_name = atom_names[index].upper()
        if atom_name.startswith("O"):
            return index

    if start < end:
        return start
    return None


def _append_protein_segment(
    segment_points: list[np.ndarray],
    segment_resids: list[int],
    segment_resnames: list[str],
    segment_elements: list[str],
    point_positions: list[np.ndarray],
    point_resnames: list[str],
    point_elements: list[str],
    point_resids: list[int],
    point_chars: list[str],
    line_starts: list[np.ndarray],
    line_ends: list[np.ndarray],
    line_chars: list[str],
    line_color_ids: list[int],
    protein_line_char: str,
    view_mode: str,
) -> None:
    if len(segment_points) < 2:
        if view_mode == "cartoon" and protein_line_char == "ss" and len(segment_points) == 1:
            point_positions.append(segment_points[0])
            point_resnames.append(segment_resnames[0])
            point_elements.append(segment_elements[0])
            point_resids.append(segment_resids[0])
            point_chars.append("o")
        return

    structure_classes = _secondary_structure_classes(np.asarray(segment_points, dtype=float))
    if view_mode == "cartoon" and protein_line_char == "ss":
        for index, structure_class in enumerate(structure_classes):
            if structure_class == "helix":
                point_positions.append(segment_points[index])
                point_resnames.append(segment_resnames[index])
                point_elements.append(segment_elements[index])
                point_resids.append(segment_resids[index])
                point_chars.append("o")

    for index in range(len(segment_points) - 1):
        line_starts.append(segment_points[index])
        line_ends.append(segment_points[index + 1])
        if protein_line_char == "ss":
            line_chars.append(_segment_char_token(structure_classes[index], structure_classes[index + 1]))
        else:
            line_chars.append(protein_line_char)
        line_color_ids.append(COLOR_IDS["protein"])


def _segment_char_token(start_class: str, end_class: str) -> str:
    if start_class == end_class == "helix":
        return "helix"
    if start_class == end_class == "sheet":
        return "sheet"
    return "auto"


def _secondary_structure_classes(points: np.ndarray) -> list[str]:
    count = len(points)
    if count == 0:
        return []
    classes = ["loop"] * count
    if count < 3:
        return classes

    for index in range(1, count - 1):
        previous_step = points[index] - points[index - 1]
        next_step = points[index + 1] - points[index]
        previous_norm = np.linalg.norm(previous_step)
        next_norm = np.linalg.norm(next_step)
        if previous_norm < 1e-6 or next_norm < 1e-6:
            continue

        bend_angle = _angle_between(-previous_step, next_step)
        bridge = np.linalg.norm(points[index + 1] - points[index - 1])
        average_step = (previous_norm + next_norm) / 2.0
        bridge_ratio = bridge / max(average_step, 1e-6)

        if 75.0 <= bend_angle <= 125.0 and bridge_ratio <= 1.65:
            classes[index] = "helix"
        elif bend_angle >= 145.0 and bridge_ratio >= 1.85:
            classes[index] = "sheet"

    classes = _suppress_short_runs(classes, "helix", HELIX_MIN_RUN)
    classes = _suppress_short_runs(classes, "sheet", SHEET_MIN_RUN)

    if count >= 2:
        classes[0] = classes[1] if classes[1] != "loop" else classes[0]
        classes[-1] = classes[-2] if classes[-2] != "loop" else classes[-1]
    return classes


def _suppress_short_runs(classes: list[str], target: str, minimum_run: int) -> list[str]:
    cleaned = classes[:]
    start = 0
    while start < len(cleaned):
        if cleaned[start] != target:
            start += 1
            continue
        end = start
        while end < len(cleaned) and cleaned[end] == target:
            end += 1
        if (end - start) < minimum_run:
            for index in range(start, end):
                cleaned[index] = "loop"
        start = end
    return cleaned


def _angle_between(vector_a: np.ndarray, vector_b: np.ndarray) -> float:
    unit_a = vector_a / max(np.linalg.norm(vector_a), 1e-6)
    unit_b = vector_b / max(np.linalg.norm(vector_b), 1e-6)
    cosine = float(np.clip(np.dot(unit_a, unit_b), -1.0, 1.0))
    return math.degrees(math.acos(cosine))
