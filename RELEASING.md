# Releasing `cmd-viewer`

This file documents the normal maintenance and release workflow for
`cmd-viewer`.

## Normal Development

For ordinary work, proceed as usual:

1. Edit code, tests, or docs.
2. Commit and push your changes.
3. Let GitHub Actions run `package-checks`.

No PyPI release is needed unless you want users installing with
`pip install cmd-viewer` to receive the change immediately.

## When A New Release Is Needed

Make a new release when the change should be reflected in the published PyPI
package. Typical examples:

- code changes
- CLI changes
- dependency changes
- important packaging metadata changes
- README changes that you want reflected on the PyPI project page

If a change only matters on GitHub, you can usually stop at commit + push.

## Versioning

Use simple semantic versioning-style increments:

- `0.1.1`, `0.1.2`: fixes, documentation, minor UX changes
- `0.2.0`, `0.3.0`: new features, new flags, larger behavior changes
- `1.0.0`: first stable release

## Release Checklist

1. Update [`CHANGELOG.md`](./CHANGELOG.md) with a new version section.
2. Bump the version in:
   - [`pyproject.toml`](./pyproject.toml)
   - [`src/cmd_viewer/__init__.py`](./src/cmd_viewer/__init__.py)
3. Run tests locally if needed.
4. Commit and push the release-prep changes.
5. Create and push a version tag.
6. Create a GitHub Release from that tag.
7. GitHub Actions publishes to PyPI automatically.

## Exact Commands

Example for releasing `v0.1.1`:

```bash
git add CHANGELOG.md pyproject.toml src/cmd_viewer/__init__.py
git commit -m "Prepare v0.1.1 release"
git push origin main
git tag v0.1.1
git push origin v0.1.1
```

Then create the GitHub Release:

- GitHub web UI:
  - open `Releases`
  - draft a new release
  - choose tag `v0.1.1`
  - title it `v0.1.1`
  - paste the relevant changelog section into the release notes
  - publish the release

- Or with GitHub CLI:

```bash
gh release create v0.1.1 --title "v0.1.1" --notes-file CHANGELOG.md
```

## Notes

- PyPI metadata only updates when a new distribution is uploaded.
- That means README or metadata changes do not appear on PyPI until the next
  release.
- The package-validation workflow should catch version mismatches and packaging
  issues before release.
