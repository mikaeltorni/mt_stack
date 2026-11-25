# Public Linux setup hub

`mt_stack` links independent public Linux setup repositories gradually migrated
from `installation_scripts`. Keep the old setup chain working.

When asked to transfer another project:

- Confirm its actual public GitHub visibility, Linux setup purpose, immutable ID and default branch. Add a link in `repositories.json`; keep private candidates out of the active registry.
- Keep each project in its own external Git checkout. Never embed its source, a repository snapshot or a Git submodule in this hub.
- Fix installer behavior in the owning repository. Every linked project needs a standalone `install.sh`, selection menu and clean-install support without required private downloads or private sibling repositories.
- Preserve owner licenses and user configuration. Keep user-mode installation sudo-free and follow the selected Linux desktop deployment policy.
- Test external checkout discovery, clone/reuse, selection, failure behavior and the owner independently. Update README and MIGRATION; distinguish local fixes from published source.
- Preserve the hub's MIT license and disclaimer. Never push, publish or change visibility unless explicitly requested.

Publication is currently blocked by private snapshots retained in older hub
commits (see `MIGRATION.md`). A clean current tree does not make that history
publishable. Before a future publication, obtain explicit authorization for a
reviewed history cleanup or clean-history release; do not rewrite history as
routine migration maintenance.

## New repository initialization

Before implementing a new stack owner, add a root `LICENSE.md` with the full
MIT text and the appropriate copyright year and holder. Add a root
`DISCLAIMER.md` matching the hub's disclaimer. Use this hub's legal files as
the templates and include both in the new owner's initial commit.

## Installer framework contract

Every new or updated owner must support the shared installer framework maintained
by `linux_installation_scripts_functions`. Keep menu behavior in that owner;
use its maintained implementation or a generated, licensed support package with
provenance and a verifiable source manifest. A clean checkout must resolve the
framework without a required private download, private sibling or prefilled cache.
Preserve explicit framework overrides for development and the old setup chain.

The standalone menu and programmatic commands must call the same operations:
`bash install.sh --list-components`, `--select ID,...`, `--default`, `--all`,
`--detect`, `--reconfigure ID,...`, `--uninstall ID,...`, and `--export-selection`.
An atomic project may expose one real component. Discovery/help/export must be
side-effect free; reject malformed input and unknown IDs before any install or
uninstall effects. Preserve documented core-only empty selections.

Verify both interfaces: exercise multi-selection, nested configuration where
present, installed-state detection, removal, cancellation and rejection through
real terminal tests and isolated CLI fixtures. The aggregate hub must retain the
same selected component IDs and action semantics as direct owner commands.
Document receipt-only removal when an owner deliberately cannot reverse an action.

Generated MIT installer support is an allowed shared library subset, not a copy
of an application repository. Retain its license and provenance; maintain and
regenerate it from the framework owner rather than editing consumer copies.
Never embed application source, private repository snapshots or submodules in
this hub. Test a fresh isolated checkout without credentials or a live desktop
before admitting an owner, and retain the existing setup-chain compatibility tests.

The hub default branch is `master`. Linked owners keep their own default branches.
The hub owns only repository registration, cloning/reuse and installer routing.
Existing checkouts are reused without pull, checkout, reset or merge. Public
owner updates remain local until the user requests publication.

After implementation and documentation changes are complete, maintain SEO through
sibling private [`seo_optimization`](../seo_optimization/AGENTS.md). First read
its `AGENTS.md`, then follow that repository's current workflow and refresh its
evidence for this hub. Keep SEO policy and scorecards there. The hub is currently
unpublished; do not claim a published audit or publish it implicitly. This
maintenance workflow is separate from installation and is not an installer dependency.
