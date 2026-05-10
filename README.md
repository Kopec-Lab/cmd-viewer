# cmd

<p align="center">
  <img src="https://raw.githubusercontent.com/Kopec-Lab/cmd-viewer/main/assets/cmd-intro.png" width="800" alt="CMD"/>
</p>

`cmd` is a terminal-first molecular dynamics viewer aimed at quick inspection of
GROMACS systems on local machines, HPC clusters, and remote shells. The first
prototype focuses on:

- `.pdb` / `.gro` structures with optional `.xtc` trajectories
- terminal-only rendering with no GUI dependencies
- water hidden by default
- atom selections that stay close to VMD workflows
- a single-command install path through `pip` or `conda` later
- responsive loading for quick trajectory sanity checks

The internal Python package is named `cmd_viewer` to avoid colliding with
Python's standard-library `cmd` module. The installed executable remains `cmd`.

## MVP design

The initial package is split into a few small layers:

- `cli.py`: argument parsing and startup
- `loader.py`: MDAnalysis universe loading and frame access
- `selection.py`: default visibility rules and VMD-like selection normalization
- `camera.py`: viewport state and 3D transforms
- `colors.py`: terminal palette and biomolecular class heuristics
- `representations.py`: mode-specific point, trace, and coarse primitives
- `render.py`: point-cloud projection into terminal cells
- `app.py`: curses event loop and playback controls

The rendering model is intentionally simple. The viewer supports a few startup
visualization modes selected with `--view-mode`:

- `points`: atom-level point cloud for fast whole-system inspection
- `trace`: residue-level backbone-like trace using `CA` / `BB` / `P` / `C4'`
- `coarse`: protein as dash traces, lipid headgroups as `O`, ions as colored `*`,
  and one coarse primitive for other non-protein residues
- `cartoon`: protein rendered as directional ASCII backbone segments, with the
  same coarse non-protein markers as `coarse`, plus a simple secondary-structure
  heuristic that distinguishes helix-, sheet-, and loop-like segments

For large systems, the renderer downsamples to a bounded number of displayed
point primitives so the viewer remains responsive over SSH and on shared
systems. The viewer also draws a small XYZ axis triad so the current
perspective remains legible, supports in-plane panning for zoomed inspection,
and can overlay orthorhombic box boundaries when unit-cell dimensions are
available.

## Install

```bash
pip install .
```

For local iteration during development:

```bash
pip install -e .
```

Once published on PyPI:

```bash
pip install cmd-viewer
```

## Release To PyPI

This repository includes a GitHub Actions workflow at
`.github/workflows/release.yml` that:

- builds an sdist and wheel
- runs `twine check` on the generated distributions
- publishes to PyPI using Trusted Publishing when a GitHub release is published
- uses the GitHub Actions environment `pypi` for an extra approval boundary

This repository also includes `.github/workflows/package-checks.yml`, which
builds the package, verifies version consistency, runs tests, and checks the
README/distributions on pushes, pull requests, and manual runs.

One-time PyPI setup:

1. In PyPI, create a pending GitHub Actions publisher for project `cmd-viewer`.
2. Point it at repository `Kopec-Lab/cmd-viewer`.
3. Set the workflow file to `.github/workflows/release.yml`.
4. Set the environment name to `pypi`.
5. Make sure the GitHub release is created from the version you want to publish.

Typical release flow:

```bash
# update CHANGELOG.md if needed
# update version in pyproject.toml and src/cmd_viewer/__init__.py if needed
git tag v0.1.1
git push origin v0.1.1
```

Then publish a GitHub release for that tag. The workflow will build the package
and upload it to PyPI automatically after the `pypi` environment rules, if any,
are satisfied.

Once published, installation on a remote machine becomes:

```bash
pip install cmd-viewer
```

## Run

```bash
cmd system.gro traj.xtc
cmd system.pdb --selection "protein or resname POPC"
cmd system.gro traj.xtc --show-water
cmd system.gro traj.xtc --view-mode trace --selection protein
cmd system.gro traj.xtc --view-mode coarse
cmd system.gro traj.xtc --selection lipids
cmd system.gro traj.xtc --selection "resname K" --color-mode resid
cmd system.gro traj.xtc --selection protein --near-water 5
cmd system.gro traj.xtc --view-mode cartoon --selection protein
cmd system.gro traj.xtc --view-mode coarse --selection "protein or resname POPC or resname CHOL or element K or element CL"
cmd system.gro traj.xtc --view-mode coarse --smooth 5
cmd system.gro traj.xtc --smooth 7 --smoothres "protein"
```

## Quick Start

Minimal launch:

```bash
cmd system.gro traj.xtc
```

Protein-centric overview:

```bash
cmd system.gro traj.xtc --selection protein --view-mode cartoon
```

Membrane-system overview:

```bash
cmd system.gro traj.xtc --selection "protein or lipids or element K or element CL" --view-mode coarse
```

If you are using the test systems in this repository:

```bash
cmd test-trajs/traak/after90ns-k.pdb test-trajs/traak/traj_comp.xtc --selection protein --view-mode cartoon
cmd test-trajs/popc/em.gro test-trajs/popc/whole.xtc --view-mode coarse
cmd test-trajs/ga/reference-structure-2M-KCl.gro test-trajs/ga/04-pt7scaling-11pA.xtc --selection "resname K" --color-mode resid
```

## Controls

- `q`: quit
- `h`: toggle help
- `space`: play / pause
- `n` or right arrow: next frame
- `b` or left arrow: previous frame
- `w` / `s`: tilt camera
- `a` / `d`: rotate camera
- `z` / `x`: roll camera
- `i` / `k`: translate view up / down
- `j` / `l`: translate view left / right
- `+` / `-`: zoom
- `r`: reset camera
- `o`: toggle box overlay

The current zoom limit is `32x`. Translation is screen-space panning, which is
useful when zoomed into a region after rotating the system.

## Smoothing

- `--smooth N` applies centered trajectory smoothing over `N` frames.
- By default smoothing targets proteins and lipid residues only.
- `--smoothres "selection"` overrides which atoms are smoothed using the same
  MDAnalysis/VMD-style selection syntax as `--selection`.
- Ions are intentionally excluded by default because they often move too far
  frame-to-frame for smoothing to look sensible.

## Dynamic Water Overlay

- `--near-water 5` shows water oxygens within `5 A` of a target selection and
  updates that subset every frame.
- The default target is `protein`, and you can override it with
  `--near-water-target "selection"`.
- These waters are rendered as thin red glyphs so hydrated pockets and pore
  pathways are easier to spot without turning on bulk water.

Examples:

```bash
cmd system.gro traj.xtc --selection protein --near-water 5
cmd system.gro traj.xtc --view-mode cartoon --selection protein --near-water 4
cmd system.gro traj.xtc --near-water 5 --near-water-target "protein or lipids"
```

## Representation Notes

- `points` is still the best default for fast whole-system checks.
- `trace` works best for proteins or nucleic-acid-heavy selections.
- `coarse` is intended for overview work: protein is shown as trace lines only,
  lipid residues try to anchor on headgroup atoms, and ions are colored by type
  in class mode following VMD-like expectations.
- `cartoon` is a protein-focused variant of `coarse` that replaces protein dash
  traces with heuristic secondary-structure-aware ASCII: helix-like segments are
  thickened with `@`/`o`, sheet-like segments use directional arrows, and loops
  fall back to lighter `=`, `|`, `/`, and `\` backbone segments.
- `--color-mode resid` is useful for tracking selected ions individually, for
  example `--selection "resname K" --color-mode resid`. Colors then cycle by
  residue id.
- Box drawing currently supports orthorhombic unit cells only.

Examples:

```bash
cmd system.gro traj.xtc --view-mode points
cmd system.gro traj.xtc --view-mode trace --selection protein
cmd system.gro traj.xtc --view-mode coarse --selection "protein or lipids"
cmd system.gro traj.xtc --view-mode cartoon --selection protein
```

## Selection notes

Selections are passed to MDAnalysis, which already supports the core concepts
needed here such as `resname`, `name`, `resid`, boolean operators, and ranges.
The viewer also normalizes `atomname` to `name`, and supports a built-in
`lipids` keyword that expands to a list of common lipid residue names.

Examples:

```bash
cmd system.gro traj.xtc --selection "protein"
cmd system.gro traj.xtc --selection "lipids"
cmd system.gro traj.xtc --selection "resname POPC or resname CHOL"
cmd system.gro traj.xtc --selection "protein or lipids"
cmd system.gro traj.xtc --selection "resid 10:50 and atomname CA"
cmd system.gro traj.xtc --selection "resname K"
cmd system.gro traj.xtc --selection "protein and around 5 resname K"
cmd system.gro traj.xtc --selection "resname POPC and name P"
```

## Usage Recipes

Quick whole-system sanity check:

```bash
cmd system.gro traj.xtc --view-mode coarse
```

Check protein orientation in the membrane:

```bash
cmd system.gro traj.xtc --selection "protein or lipids" --view-mode coarse
```

Inspect secondary-structure-like protein shape:

```bash
cmd system.gro traj.xtc --selection protein --view-mode cartoon
```

Follow a specific ion type through a pore:

```bash
cmd system.gro traj.xtc --selection "resname K" --color-mode resid
cmd system.gro traj.xtc --selection "resname CL" --color-mode resid
```

Show only nearby hydration around the protein:

```bash
cmd system.gro traj.xtc --selection protein --near-water 5
```

Use smoothing for protein and lipid motions:

```bash
cmd system.gro traj.xtc --view-mode coarse --smooth 5
```

Smooth only the protein:

```bash
cmd system.gro traj.xtc --view-mode cartoon --smooth 7 --smoothres "protein"
```

Inspect a residue range or local region:

```bash
cmd system.gro traj.xtc --selection "resid 50:120"
cmd system.gro traj.xtc --selection "protein and around 6 resname LIG"
```

## Roadmap

- improve playback performance for very large systems
- add residue / chain / segment centering shortcuts
- add small-selection ball-and-stick or stick-like modes
- support saved views and screenshots
- package for conda-based HPC installation
