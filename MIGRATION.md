# Linked repository migration audit

## Public release on 2026-11-25

MT Stack was published from a reviewed source snapshot at
[mikaeltorni/mt_stack](https://github.com/mikaeltorni/mt_stack) on `master`.
An anonymous clone matched the reviewed source tree and contained no bundled
owner repositories. The default workstation profile resolves 53 component IDs
across 13 public owners. Programming Prompts is a content source consumed by
Linux CLI Setup and Programming Setup.

### Seven optional public owners

The seven repositories below were added to both MT Stack profiles as optional
owners with their own standalone installers. Each was cloned anonymously in
the Ubuntu 24.04.5 guest. Their first commits contain the MIT license and a
disclaimer, and the rewritten history retains the original commit timestamps
and parent relationships.

| Repository | Verified release revision | Ubuntu VM verification |
| --- | --- | --- |
| `linux_installation_scripts_functions` | `33d7d13` | Component lifecycle, installer modules and standalone deployment |
| `claude_code_status_bar` | `9ec8bfc` | Installer and status-line tests, 24 passed and 1 skipped |
| `linux_taskbar_agentic_coding_cli_status_bar` | `c706ddb` | 324 Rust tests and 106 installer assertions |
| `linux_kitty_terminal_description` | `ba1fdc2` | Standalone checks and 8 tests |
| `linux_lmstudio_local_agents` | `81fedf2` | 30 tests including the clean-user Rust cache path |
| `linux_codex_claude_code_tts_announcements` | `55b681d` | 25 tests including the standalone install |
| `linux_luks_configuration` | `b9c6920` | 9 checks and encrypted data preservation using a disposable VM disk |

The records below describe earlier work and test environments. Visibility and
revision statements in those records apply to their audit dates.

## Earlier workstation and repository checks

The opt-in `--workstation` profile keeps workstation owner checkouts separate
from the public registry. It reuses external Git checkouts or, with explicit
`--fetch`, clones them with the workstation owner's configured Git access.
Foundation packages and GNOME configuration precede the desktop and
programming tools. The coding CLI setup and Agent Command Center remain opt-in.

Workstation validation cloned the 13 default owners from GitHub with
authenticated Git discovery. On the Ubuntu 24.04.5 X11 VM, MT Stack
`81d83ed` and Programming Setup `78e41af` ran the complete default profile
twice with separate owner checkouts and no `installation_scripts` checkout.
The first run fetched the public prompt source. Installed-state checks found
52 of 53 default components and nine active GNOME extensions. The VM lacks a
mouse Back button for the remaining tiling component. Both runs retained the
guest boot ID and the existing pointer size setting. The validation used
local commits for the hub and Programming Setup fixes.

Audited 2026-10-22 against the owner's current public GitHub inventory and each
linked repository's metadata. `mt_stack` is a central hub on `master`, not a
container for project source. Its active registry links only these five public
Linux setup projects. Their default branch names remain independent of the hub.

| Public owner | Default branch | Published HEAD at audit | Local standalone installer fix |
| --- | --- | --- | --- |
| [programming_prompts](https://github.com/mikaeltorni/programming_prompts) | `master` | `18068f78ada5e1b9ad7fbc531cee806a0eb41d2b` | `54ae47b7813c7d9018dbcd89422158ec6925d54d` |
| [codex](https://github.com/mikaeltorni/codex) | `main` | `99fcf7b19a30652da9363581d4fdb95241e112ca` | `537c4d546964617d12553b16309998f14e65da2a` |
| [linux_automatic_window_tiling](https://github.com/mikaeltorni/linux_automatic_window_tiling) | `master` | `f28ac8c4376d3edb30d5d7f96cf4c638ad4ae2f0` | `9a933c2245d590bf290a0c1db19c1ffbf121cc34` |
| [linux_taskbar_window_count](https://github.com/mikaeltorni/linux_taskbar_window_count) | `master` | `1c20a2709864f664fa1a5a55f09864192654d986` | Existing standalone installer; unchanged |
| [linux_taskbar_monitor](https://github.com/mikaeltorni/linux_taskbar_monitor) | `master` | `1ea6f7089c86e9ceac33b99b652bce506ad26d18` | `cc30520e60193678bdacc34a0c74741c8d8ddc09` |

## Local delivery and publication

All source changes are committed and merged into each owner's local default
branch. This task did not push, publish, rename or change visibility on GitHub.
A private GitHub remote exists; this task did not push it or change its remote default branch. The local hub default remains master. The source snapshots and private extractions from the
initial implementation were removed from its current tree; history was not rewritten.
Commit `812d011` still contains the private repository snapshots under
`repositories/`. **Do not publish the existing Git history or make its private
remote public.** An explicitly authorized history cleanup or reviewed clean-history
release must precede publication. Current-tree installer checks do not audit or
remove historical private content.
Only ignored caches remained after that removal, and those artifacts were moved
outside the live hub into its task checkout's temporary directory.

The active installation flow clones/reuses `~/projects/<owner>` (or an explicit
external `--projects-dir`), verifies its Git origin, and runs its own `install.sh`.
Existing checkout contents and branches are retained. There are no embedded
owners, submodules, fallback private clones, or private CLI installer copies in
the hub. The hub does not install a separately cloned shared framework.

The public prompt owner now has native skill components; the public Codex owner
has its own source-build component. Tiling and monitoring carry their required
MIT installer support in their own `.installer-support/` directories, including
standalone selection export fixes. The support's original license and provenance
are retained there. None requires access to a private repository. Badge
installation was already self-contained.

A further prompt-owner regression verified real repeated Codex/Claude skill
installation and found that unknown explicit component IDs silently succeeded.
The prompt-owned runtime now validates component membership before any install
effects; the retained rejection check preserves existing skills and user files.

At the initial audit, these owner changes were local and unpublished. The final
follow-up verified that public prompts/Codex still lack their new root entrypoint,
while tiling and monitoring now publish their prepared standalone support.
This follow-up did not perform those publications; its new repairs remain local. The hub detects
a missing root installer and stops with a publication explanation. Existing local
owners are usable now. Successful fixture clone tests verify orchestration; they
do not claim that unpublished commits are served by GitHub.

## Pending candidates and exclusions

`linux_codex_claude_code_setup` and `linux_installation_scripts_functions` are
still private and excluded from the active registry. Do not add a private clone
URL, copy their repositories into the hub, or change visibility automatically.
The CLI setup may join the hub after the owner explicitly publishes it and its
required dependencies pass the public standalone criteria.

Other private setup projects remain outside this migration. Public repositories
unrelated to this Linux setup chain are also excluded: `coding_tools`,
`prompt_engineering_for_software_development`, `prompt_challenge_generator`,
`luna_prompts_contest_solutions`, and `FluxImageGenerationAgentSystem`.

`linux_git_folder_counts` is published privately on GitHub with default branch
`master` and immutable ID `R_kgDOVznghw`. The owner has an
MIT license, the stack disclaimer, and an offline-capable shared installer
support package. The GTK modules display red unpushed and light-purple
off-master counts before repository names. The owner tests cover GTK 3 and
GTK 4 choosers, GNOME Files list and grid views, and installer lifecycle.
An isolated hub fixture also exercised cloning, selection, detection,
reconfiguration, and removal using the real owner. Active registration
requires its verified public GitHub repository ID and default branch.

## Standalone migration preparation

On 2026-11-19 GitHub reported private visibility for the 22 additional owners
in the migration inventory. Their active registration is pending. In an
isolated hub fixture, 21 of those owners were cloned from their actual local
default-branch trees using a Git URL rewrite, discovered through their
`install.sh`, and reused offline. LUKS Configuration was tested separately
inside a disposable guest. The hub fixture verified routing and component
discovery. A clean GitHub install
still needs accessible owner releases and installation validation.

Window Selection Indicator now detects its disabled outline as absent.
Active Monitor Placement has standalone installation documentation and a
disclaimer. Task Workspaces and the two CLI setup and status-bar owners
received installer test updates. The TTS owner keeps install banners out of
component discovery. These changes were prepared locally.

Agent Command Center delegates required setup to CLI Setup and Window
Selection Indicator. Linux Configuration Setup now delegates its existing
Active Monitor Placement component to the standalone installer when a sibling
checkout is present. Its bundled fallback keeps the original installer
usable while the owner is private. Isolated tests cover both paths.
LUKS runtime checks ran in an isolated Ubuntu 24.04 QEMU/KVM guest with a
dedicated 192 MiB disk. Commit `defa34f` fixes a baseline failure where the
standalone installer formatted the test disk even after it warned that
consent was missing. The repaired installer rejected missing consent and
incorrect device confirmation, and passed explicit install, detection,
closed-volume reconfiguration, and receipt-only removal with data retained.
The host installer path was exercised only by static checks.

MT Stack suppresses reboot requests made by child installers that honor the
original chain's suppression flags. Each owner continues to implement its own
installation operations.

## Checks and future maintenance

Hub tests cover external public-URL fixture clones, unchanged reuse, offline
rejection, malformed selections, unrelated origins, paths inside the hub,
component discovery/selection and terminal interaction. All five real local
owners exposed their component lists through the hub with `--offline`.
The 2026-10-23 Ubuntu 24.04.5 / GNOME 46 X11 VM run additionally verified
all-five installation, repeat installation, real owner menu cancellation and
component application, both tiling shortcuts, correct workspace badge counts,
and live monitor metrics/popups. Codex and its companion were built from source;
the installed Code Mode IPC evaluated `6 * 7` to `42`. Both executable names
worked in a fresh login shell and the existing desktop terminal. No authenticated
model request, actual quota-reset event, reboot or host desktop reload was tested.

Demonstrated defects were repaired in their owners and redeployed to the VM:

| Owner | Local repair commits |
| --- | --- |
| tiling | `889f43b` unknown-selection rejection; `c86b86f` stream-safe export |
| badges | `c24f983` GNOME-compatible text shadow |
| prompts | `925cbc8` stream-safe export; `7c5af67` successful menu cancellation |
| monitor | `534b532` stream-safe export; `532b953` explicit framework fallback; `e041993` deferred interactive deployment; `584c60c` preservation of existing patches |

The reproducible VM runner commands and coverage limits are in the root README.
All these fixes are committed and merged into local owner default branches.
They have not been pushed by this task.

## Final audit after VM removal

The VM is no longer available; no reconnect or new desktop run was attempted.
Local hub and all five owner installer checks were rerun. Follow-up repairs are
`1b5c5b9` (hub incompatible component options), `d9bc8bf` (tiling fixtures preserve
editor symlinks), and `24bbaa7` (monitor rejects malformed action operand counts
before download or desktop effects). Each has a saved failing regression and
passing retained checks, and is merged into its owner's local `master`.

The five public GitHub identities, public visibility and owner default branches
were rechecked against the registry. Published tiling HEAD was `3134e7f` and
monitor HEAD was `c8e10e7`; both included their standalone support. The GitHub
contents API returned 404 for root installers in prompts and Codex. The hub itself remains private remotely;
its local default is `master`. No push, visibility change or history rewrite
was performed. Native Codex and live GNOME coverage above describe the earlier
VM run; the final argument/fixture changes have local verification only.

SEO maintenance is delegated by the short instruction in `AGENTS.md` to the
private `seo_optimization/AGENTS.md` workflow. No scorecard or SEO policy is copied
into this public-facing hub, and no published SEO score is claimed for this
unpublished local repository.

## 2026-10-25 installer lifecycle preparation (local only)

The hub now uses the maintained aggregate component menu: arrow/Space selection,
per-owner details, reconfiguration, removal and cancellation. CLI and menu actions
share one execution path. `--all`, `--detect`, `--export-selection`,
`--reconfigure OWNERS` and `--uninstall OWNERS` complement named selection;
repeated `--components OWNER=IDs` preserves exact selections for several owners.
The README documents empty selections and maintenance defaults.

Nineteen private candidate installers and four public shared-support owners now
carry the same generated MIT support subset; Window Count retains its compatible
native adapter. The private framework owner maintains the exporter, source
manifest, license and regressions. Bundled support resolves offline by default,
with explicit development/old-chain overrides retained. These changes remove
required private framework downloads; project runtime/provider dependencies
remain owner-specific. No private application source was embedded in this hub.

Phrase Automation retains a complete MIT grant and a separate compatible
disclaimer. Its repository remains private. The admission contract in AGENTS.md
requires this shared lifecycle and clean-checkout verification for future owners.

Public root-entrypoint fixtures cover malformed/unknown/duplicate/conflicting
requests before effects, state preservation, install/reconfigure/removal, and
side-effect-free discovery/export. Real PTYs verify selection, nested screens,
cancellation and exact CLI action parity. Repairs include strict-Bash cancellation,
stream-safe JSON export, detector diagnostics outside query output, planning
before log pipes, and read-only status previews that do not build native tools.
The framework retained suite passed 215 tests; the original setup-chain component
and repository-manifest suite passed 43 tests. Owner-specific retained suites and
build checks are recorded in the private maintenance evidence.

This run used isolated homes, temporary state and mocked external actions.
LUKS checks were static only. No host power helper, full OS installation, live
extension-code deployment, authenticated model request or new full Codex build
was executed. Earlier VM evidence above remains bound to that earlier revision.

GitHub metadata was freshly checked by immutable identity: five active public
links, twenty private roadmap candidates/framework projects and the private hub.
All implementation commits were merged into local owner default branches; no
push, publication, visibility change or history rewrite was performed. The
historical private-snapshot publication blocker remains unresolved.


The final old-chain integration check additionally reproduced safe shared-router
owners being classified as atomic by `installation_scripts`' legacy source
probe. Owner commit `2913687` now recognizes both `component_main` and
`isc_route_readonly_args`, including delegated standalone wrappers; documentation
commit `1658a38` records that boundary. A saved public aggregate-discovery fixture
retains router/delegated/legacy component IDs and defaults while proving atomic
installers are never probed. It and all 43 retained component/manifest tests pass.
All nineteen affected private owner entrypoints also pass the static awareness
check without executing any installer. These original-orchestrator commits were
merged locally; its unrelated README, dependency and manifest drafts were retained.
