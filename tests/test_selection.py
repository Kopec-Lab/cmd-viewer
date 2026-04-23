from cmd_viewer.selection import build_selection, normalize_selection


def test_normalize_selection_rewrites_atomname() -> None:
    assert normalize_selection("resid 1:10 and atomname CA") == "resid 1:10 and name CA"


def test_build_selection_hides_water_by_default() -> None:
    result = build_selection("protein", show_water=False)
    assert "protein" in result
    assert "resname SOL" in result


def test_normalize_selection_expands_lipids_keyword() -> None:
    result = normalize_selection("protein or lipids")
    assert "protein or (" in result
    assert "resname POPC" in result
    assert "resname DPPC" in result
