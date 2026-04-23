from __future__ import annotations

import curses
import time

import numpy as np

from cmd_viewer.camera import Camera
from cmd_viewer.loader import load_system
from cmd_viewer.overlays import POCKET_WATER_COLOR_ID, PocketWaterOverlay
from cmd_viewer.representations import build_frame_payload
from cmd_viewer.render import TerminalRenderer
from cmd_viewer.smoothing import TrajectorySmoother


HEADER_LINE_COUNT = 2
ROTATION_STEP = 0.08
ZOOM_FACTOR = 1.15
PAN_STEP_X = 4.0
PAN_STEP_Y = 2.0
PLAYBACK_INTERVAL = 0.08
FRAME_SLEEP = 0.01


HELP_LINES = [
    "q quit",
    "space play/pause",
    "n/right next frame",
    "b/left previous frame",
    "w/s tilt",
    "a/d rotate",
    "z/x roll",
    "i/k up/down",
    "j/l left/right",
    "+/- zoom",
    "r reset",
    "o box on/off",
    "h hide help",
]


def run_viewer(args) -> None:
    system = load_system(
        structure_path=args.structure,
        trajectory_path=args.trajectory,
        selection=args.selection,
        show_water=args.show_water,
    )
    curses.wrapper(_run_curses_app, system, args)


def _run_curses_app(screen: "curses.window", system, args) -> None:
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    screen.nodelay(True)
    screen.keypad(True)

    renderer = TerminalRenderer(color_mode=args.color_mode)
    renderer.init_colors()
    camera = Camera()
    smoother = TrajectorySmoother(
        universe=system.universe,
        atoms=system.atoms,
        window=args.smooth,
        smooth_selection=args.smoothres,
    )
    pocket_water = PocketWaterOverlay(
        universe=system.universe,
        cutoff=args.near_water,
        target_selection=args.near_water_target,
    )
    resnames = system.atoms.resnames.tolist()
    elements = _elements_for_atoms(system.atoms)
    atom_names = system.atoms.names.tolist()
    resids = system.atoms.resids.tolist()

    show_help = True
    show_box = True
    playing = False
    frame_stride = max(args.stride, 1)
    frame_index = _clamp_frame(args.start_frame, system.frame_count)
    last_advance = time.monotonic()

    while True:
        system.universe.trajectory[frame_index]
        positions = smoother.smooth_positions(frame_index, system.atoms.positions.copy())
        center = positions.mean(axis=0, keepdims=True)
        box_corners = _orthorhombic_box_corners(system.universe.trajectory.ts.dimensions)

        total_height, total_width = screen.getmaxyx()
        footer_lines = _footer_lines(show_help, total_width, args.color_mode, args.view_mode)
        view_height = max(total_height - HEADER_LINE_COUNT - len(footer_lines), 1)
        payload = build_frame_payload(
            view_mode=args.view_mode,
            positions=positions,
            resnames=resnames,
            elements=elements,
            atom_names=atom_names,
            resids=resids,
            center=center,
            box_corners=box_corners,
            max_points=args.max_points,
            width=total_width,
            height=view_height,
        )
        overlay_positions = pocket_water.positions()
        if len(overlay_positions):
            payload.overlay_positions = overlay_positions
            payload.overlay_chars = ["."] * len(overlay_positions)
            payload.overlay_color_ids = [POCKET_WATER_COLOR_ID] * len(overlay_positions)
        header_lines = [
            (
                f"cmd  frame {frame_index + 1}/{system.frame_count}  "
                f"view {payload.view_mode}  primitives {payload.displayed_count}  "
                f"atoms {payload.atom_count}  "
                f"selection [{system.selection}]"
            ),
            (
                f"source {system.structure_path.name}"
                + (f" + {system.trajectory_path.name}" if system.trajectory_path else "")
                + f"  zoom {camera.zoom:.2f}  rotation 3-axis"
                + f"  pan ({camera.pan_x:.0f},{camera.pan_y:.0f})"
                + _smoothing_status(smoother.config)
                + _pocket_water_status(pocket_water, payload)
                + f"  box {'on' if show_box else 'off'}"
            ),
        ]
        renderer.draw(
            screen=screen,
            camera=camera,
            payload=payload,
            header_lines=header_lines,
            footer_lines=footer_lines,
            show_box=show_box,
        )

        key = screen.getch()
        if key != -1 and _handle_key(key, camera):
            break

        if key != -1:
            if key in (ord("h"), ord("H")):
                show_help = not show_help
            elif key in (ord(" "),):
                playing = not playing
            elif key in (ord("o"), ord("O")):
                show_box = not show_box
            elif key in (ord("n"), ord("N"), curses.KEY_RIGHT):
                frame_index = _advance_frame(frame_index, system.frame_count, frame_stride)
                playing = False
            elif key in (ord("b"), ord("B"), curses.KEY_LEFT):
                frame_index = _advance_frame(frame_index, system.frame_count, -frame_stride)
                playing = False

        now = time.monotonic()
        if playing and (now - last_advance) >= PLAYBACK_INTERVAL:
            frame_index = _advance_frame(frame_index, system.frame_count, frame_stride)
            last_advance = now
        elif not playing:
            last_advance = now

        time.sleep(FRAME_SLEEP)


def _handle_key(key: int, camera: Camera) -> bool:
    if key in (ord("q"), ord("Q")):
        return True
    if key in (ord("a"), ord("A")):
        camera.rotate(delta_yaw=-ROTATION_STEP)
    elif key in (ord("d"), ord("D")):
        camera.rotate(delta_yaw=ROTATION_STEP)
    elif key in (ord("w"), ord("W")):
        camera.rotate(delta_pitch=-ROTATION_STEP)
    elif key in (ord("s"), ord("S")):
        camera.rotate(delta_pitch=ROTATION_STEP)
    elif key in (ord("z"), ord("Z")):
        camera.rotate(delta_roll=-ROTATION_STEP)
    elif key in (ord("x"), ord("X")):
        camera.rotate(delta_roll=ROTATION_STEP)
    elif key in (ord("j"), ord("J")):
        camera.translate(delta_x=-PAN_STEP_X)
    elif key in (ord("l"), ord("L")):
        camera.translate(delta_x=PAN_STEP_X)
    elif key in (ord("i"), ord("I")):
        camera.translate(delta_y=-PAN_STEP_Y)
    elif key in (ord("k"), ord("K")):
        camera.translate(delta_y=PAN_STEP_Y)
    elif key in (ord("+"), ord("=")):
        camera.change_zoom(ZOOM_FACTOR)
    elif key in (ord("-"), ord("_")):
        camera.change_zoom(1 / ZOOM_FACTOR)
    elif key in (ord("r"), ord("R")):
        camera.reset()
    return False


def _advance_frame(current: int, frame_count: int, delta: int) -> int:
    if frame_count <= 1:
        return 0
    return (current + delta) % frame_count


def _clamp_frame(frame_index: int, frame_count: int) -> int:
    if frame_count <= 1:
        return 0
    return max(0, min(frame_index, frame_count - 1))


def _footer_lines(show_help: bool, width: int, color_mode: str, view_mode: str) -> list[str]:
    legend_line = _legend_line(color_mode, view_mode)
    controls = "  ".join(HELP_LINES)
    if not show_help:
        return _wrap_footer_lines([legend_line, "h help"], width)
    if len(controls) <= width:
        return _wrap_footer_lines([legend_line, controls], width)
    return _wrap_footer_lines([legend_line, *HELP_LINES], width)


def _legend_line(color_mode: str, view_mode: str) -> str:
    if view_mode == "trace":
        return "legend o trace node  - protein path  :/+ box"
    if view_mode == "cartoon":
        return r"legend @ helix  >/</^/v sheet  =|/\ loop  O lipid  * ion  D ligand  . water"
    if view_mode == "coarse":
        return "legend - protein trace  O lipid headgroup  * ion(type colors)  D ligand  . water"
    if color_mode == "resid":
        return "legend residue-id colors"
    if color_mode == "class":
        return "legend @ protein  = lipid  * ion  + ligand  . water  :/+ box"
    return "legend shades=depth  colors highlight element identity"


def _smoothing_status(config) -> str:
    if not config.enabled:
        return ""
    return f"  smooth {config.window}f/{config.smoothed_atom_count}"


def _pocket_water_status(overlay: PocketWaterOverlay, payload) -> str:
    if not overlay.config.enabled:
        return ""
    return f"  nearH2O {overlay.config.cutoff:.1f}A/{len(payload.overlay_positions)}"


def _wrap_footer_lines(lines: list[str], width: int) -> list[str]:
    wrapped: list[str] = []
    for line in lines:
        if len(line) <= width:
            wrapped.append(line)
            continue
        start = 0
        while start < len(line):
            wrapped.append(line[start : start + width])
            start += width
    return wrapped


def _elements_for_atoms(atoms) -> list[str]:
    if hasattr(atoms, "elements"):
        try:
            return atoms.elements.tolist()
        except Exception:
            pass
    return [_guess_element(name) for name in atoms.names.tolist()]


def _guess_element(name: str) -> str:
    letters = "".join(character for character in name if character.isalpha())
    if not letters:
        return "C"
    if len(letters) >= 2 and letters[:2].title() in {"Cl", "Na", "Ca", "Mg", "Zn"}:
        return letters[:2]
    return letters[0]


def _orthorhombic_box_corners(dimensions) -> np.ndarray | None:
    if dimensions is None or len(dimensions) < 6:
        return None
    lengths = np.asarray(dimensions[:3], dtype=float)
    angles = np.asarray(dimensions[3:6], dtype=float)
    if np.any(lengths <= 0.0):
        return None
    if not np.allclose(angles, np.array([90.0, 90.0, 90.0]), atol=1.0):
        return None
    lx, ly, lz = lengths.tolist()
    return np.array(
        [
            [0.0, 0.0, 0.0],
            [lx, 0.0, 0.0],
            [0.0, ly, 0.0],
            [lx, ly, 0.0],
            [0.0, 0.0, lz],
            [lx, 0.0, lz],
            [0.0, ly, lz],
            [lx, ly, lz],
        ]
    )
