import numpy as np

from cmd_viewer.smoothing import DEFAULT_SMOOTH_SELECTION, _window_bounds


def test_window_bounds_centered_and_clamped() -> None:
    assert _window_bounds(0, 10, 5) == (0, 5)
    assert _window_bounds(5, 10, 5) == (3, 8)
    assert _window_bounds(9, 10, 5) == (5, 10)


def test_default_smoothing_selection_targets_protein_and_lipids() -> None:
    assert "protein" in DEFAULT_SMOOTH_SELECTION
    assert "resname POPC" in DEFAULT_SMOOTH_SELECTION
