# Changelog

All notable changes to `cmd-viewer` will be documented in this file.

## [Unreleased]

No unreleased changes currently.

## [0.1.1] - 2026-05-17

### Added

- Explicit support and documentation for OpenMM-style `.pdb + .dcd`
  trajectory loading, backed by a regression test.

## [0.1.0] - 2026-05-10

Initial public release.

### Added

- Terminal-first MD trajectory viewer with a `cmd` console entry point.
- MDAnalysis-based loading for `.pdb` / `.gro` structures and optional `.xtc`
  trajectories.
- VMD-like selection workflow, including hidden water by default and a built-in
  `lipids` selection alias.
- Multiple terminal view modes: `points`, `trace`, `coarse`, and `cartoon`.
- Camera rotation, zoom, panning, playback, axis overlay, and orthorhombic box
  overlay controls.
- Residue, element, and class coloring modes, including ion-type-specific
  coloring and `resid` coloring for ion tracking.
- Optional trajectory smoothing for proteins and lipids.
- Dynamic near-water overlay for hydrated pocket and pore inspection.
- GitHub Actions workflows for package validation and Trusted Publishing to
  PyPI.
