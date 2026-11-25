"""Select and install separate public Linux setup repositories."""
import argparse
import json
import os
import re
import shlex
import tempfile
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def parse_identifier(text):
    """Recognize one complete owner or component identifier without domain lookups.

    Parameters: text - raw identifier token.
    Returns: the accepted identifier unchanged, or a syntax error.
    """
    print(f'text={text!r}', file=sys.stderr)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]*', text):
        raise argparse.ArgumentTypeError('expected one owner or component identifier')
    print(text, file=sys.stderr)
    return text


def parse_identifier_list(text, allow_empty):
    """Convert a complete comma-separated identifier list before dispatch.

    Parameters: text - raw operand text; allow_empty - preserve an explicit empty component selection.
    Returns: a tuple of syntactically accepted identifier strings.
    """
    print(f'text={text!r} allow_empty={allow_empty!r}', file=sys.stderr)
    result = () if not text and allow_empty else tuple(parse_identifier(token) for token in text.split(','))
    print(result, file=sys.stderr)
    return result


def parse_repository_ids(text):
    """Parse the required owner list for installation or maintenance.

    Parameters: text - raw comma-separated owner operand.
    Returns: a nonempty tuple of syntactically accepted owner identifiers.
    """
    print(f'text={text!r}', file=sys.stderr)
    result = parse_identifier_list(text, False)
    print(result, file=sys.stderr)
    return result


def parse_arguments(arguments):
    """Convert installer syntax once.
    Parameters: arguments - raw command line argument strings.
    Returns: a dispatch selector, converted operation arguments and profile flag/path tuple.
    """
    print(f'arguments={arguments!r}', file=sys.stderr)
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--list-components', type=parse_identifier, metavar='REPOSITORY', help='list components from one linked owner')
    mode.add_argument('--configure', type=parse_identifier, metavar='REPOSITORY', help='open one owner selection menu')
    mode.add_argument('--check', action='store_true', help='validate Linux scope and portable installer contracts')
    mode.add_argument('--menu', action='store_true', help='choose repositories and components interactively')
    mode.add_argument('--list', action='store_true', help='list repository names and purposes')
    mode.add_argument('--select', type=parse_repository_ids, help='install exactly these comma-separated repositories')
    mode.add_argument('--default', action='store_true', help='install the default selection')
    mode.add_argument('--all', action='store_true', help='install every component of every linked owner')
    mode.add_argument('--uninstall', type=parse_repository_ids, metavar='REPOSITORIES', help='remove selected owner components')
    mode.add_argument('--reconfigure', type=parse_repository_ids, metavar='REPOSITORIES', help='reapply selected or installed owner components')
    mode.add_argument('--detect', action='store_true', help='show owner, component and installed/absent state')
    mode.add_argument('--export-selection', action='store_true', help='export registry defaults in the shared master configuration format')
    parser.add_argument('--components', action='append', type=parse_component_assignment, help='IDs for one owner, or repeated OWNER=IDs for multiple owners')
    parser.add_argument('--projects-dir', type=lambda text: Path(text).expanduser().resolve(), default=Path(os.environ.get('MT_STACK_PROJECTS_DIR', str(Path.home()/'projects'))).expanduser().resolve(), help='external directory holding sibling checkouts')
    parser.add_argument('--offline', action='store_true', help='require existing checkouts; never clone')
    parser.add_argument('--workstation', action='store_true', help='use the opt-in profile of existing workstation owner checkouts')
    parser.add_argument('--fetch', action='store_true', help='with --workstation, clone missing owners using configured Git credentials')
    parser.add_argument('--dry-run', action='store_true', help='show installation commands without running them')
    options = parser.parse_args(arguments)
    if options.fetch and (not options.workstation or options.offline):
        parser.error('--fetch requires --workstation and cannot be combined with --offline')
    options.offline = options.offline or (options.workstation and not options.fetch)
    if options.components is not None:
        options.components = tuple(options.components)
    if options.components is not None and any((options.list, options.check,
                                               options.list_components is not None,
                                               options.configure is not None, options.menu, options.detect, options.export_selection)):
        parser.error('--components requires an installation selection')
    options.action = 'uninstall' if options.uninstall is not None else 'reconfigure' if options.reconfigure is not None else 'all' if options.all else 'install'
    options.owners = options.uninstall if options.uninstall is not None else options.reconfigure if options.reconfigure is not None else options.select
    options.query = 'detect' if options.detect else 'export' if options.export_selection else None
    options.owner = options.list_components or options.configure
    options.configure_owner = options.configure is not None
    options.registry_query = 'check' if options.check else 'list' if options.list else None
    if options.owner is not None:
        result = 'owner', (options.owner, options.projects_dir, options.offline, options.dry_run, options.configure_owner)
    elif options.query is not None:
        result = 'query', (options.query, options.projects_dir, options.offline, options.dry_run)
    elif options.registry_query is not None:
        result = 'registry', (options.registry_query,)
    else:
        interface = 'menu' if options.menu else 'auto' if not options.default and options.select is None and options.components is None and options.action == 'install' else 'cli'
        result = 'apply', (interface, options.owners, options.dry_run, options.projects_dir, options.offline, options.components, options.action)
    result = (*result, (options.workstation, options.projects_dir))
    print(result, file=sys.stderr)
    return result


def load_manifest(workstation, projects):
    """Load and validate the selected repository profile.
    Parameters: workstation - whether to use existing workstation checkouts; projects - resolved projects parent.
    Returns: ordered validated metadata, including which optional workstation owners may be fetched.
    """
    print(f'workstation={workstation!r} projects={projects!r}', file=sys.stderr)
    result = json.loads((ROOT / ('workstation.json' if workstation else 'repositories.json')).read_text())
    if workstation:
        linked = json.loads((ROOT / 'repositories.json').read_text())
        validate_manifest(linked, False)
        public_owners = {row['name'] for row in linked}
        for row in result:
            row['source'] = 'https://github.com/mikaeltorni/' + row['name']
            row['installer'] = 'install.sh'
            row['kind'] = 'local'
            row['default'] = bool(row['default_components'])
            row['default_components'] = tuple(row['default_components'])
            row['fetch_optional'] = row['name'] in public_owners
    validate_manifest(result, workstation)
    if workstation:
        for row in result:
            if row['name'] == 'linux_programming_setup':
                row['environment'] = {
                    'PROJECTS_DIR': str(projects),
                    'PROGRAMMING_PROMPTS_DIR': str(projects / 'programming_prompts'),
                    'CURSOR_SKILLS_REPOS': ' '.join(owner['name'] for owner in result),
                }
    print(result, file=sys.stderr)
    return result


def validate_selection(names, manifest):
    """Accept a nonempty set of known named entries.
    Parameters: names - converted entry names; manifest - available named records.
    Returns: selected records in registry order.
    """
    print(f'names={names!r}, manifest={manifest!r}', file=sys.stderr)
    available = {row['name'] for row in manifest}
    if not names or any(name not in available for name in names):
        raise ValueError('select one or more known repository names; use --list')
    if len(set(names)) != len(names):
        raise ValueError('duplicate repository selection')
    result = [row for row in manifest if row['name'] in names]
    print(result, file=sys.stderr)
    return result


def require_external_path(path):
    """Require checkout storage outside both the task and live hub.
    Parameters: path - resolved checkout directory or parent path.
    Returns: the accepted external path.
    """
    print(f'path={path!r}', file=sys.stderr)
    common = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', '--git-common-dir'], text=True).strip()
    live = (ROOT / common).resolve().parent
    if any(path == hub or hub in path.parents for hub in (ROOT, live)):
        raise ValueError('linked repositories must be outside mt_stack')
    print(path, file=sys.stderr)
    return path


def require_checkout(checkout, row):
    """Require a genuine external checkout of the registered owner.
    Parameters: checkout - resolved checkout path; row - repository record.
    Returns: the accepted checkout path.
    """
    print(f'checkout={checkout!r}, row={row!r}', file=sys.stderr)
    require_external_path(checkout)
    top = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', '--show-toplevel'], text=True).strip()
    remote = subprocess.check_output(['git', '-C', str(checkout), 'config', '--get', 'remote.origin.url'], text=True).strip()
    expected = row['source']
    aliases = {expected, expected+'.git', expected.replace('https://github.com/', 'git@github.com:')+'.git'}
    if Path(top).resolve() != checkout or remote not in aliases:
        raise ValueError(f"{row['name']}: existing path is not its registered Git checkout")
    if not (checkout / row['installer']).is_file():
        raise ValueError(f"{row['name']}: owner install.sh is missing from the checkout")
    print(checkout, file=sys.stderr)
    return checkout


def validate_missing_checkout(checkout, offline):
    """Reject a missing owner when the caller forbids cloning.

    Parameters: checkout - resolved absent owner path; offline - forbid network cloning.
    Returns: None when the requested missing checkout may be cloned or previewed.
    """
    print(f'checkout={checkout!r} offline={offline!r}', file=sys.stderr)
    if offline:
        raise ValueError(f'{checkout.name}: checkout missing in offline mode')
    print(None, file=sys.stderr)


def ensure_checkout(row, projects, offline, dry_run):
    """Clone an eligible missing owner or reuse a validated checkout unchanged.
    Parameters: row - owner metadata; projects - external parent; offline - reject missing owners; dry_run - preview without writes.
    Returns: the accepted or previewed checkout path.
    """
    print(f'row={row!r}, projects={projects!r}, offline={offline!r}, dry_run={dry_run!r}', file=sys.stderr)
    projects = require_external_path(projects)
    checkout = require_external_path((projects / row['name']).resolve())
    if checkout.exists():
        require_checkout(checkout, row)
    else:
        validate_missing_checkout(checkout, offline)
        if row['kind'] == 'local':
            command = ['git', 'clone', '--single-branch', '--', row['source'] + '.git']
        else:
            command = ['git', '-c', 'credential.helper=', 'clone', '--single-branch', '--branch', row['branch'], '--', row['source'] + '.git']
        print(shlex.join([*command, str(checkout)]), file=sys.stdout if dry_run else sys.stderr)
        if not dry_run:
            projects.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='.mt-stack-clone-', dir=projects) as temporary:
                staged = Path(temporary)/row['name']
                subprocess.run([*command, str(staged)], check=True, env=dict(os.environ, GIT_TERMINAL_PROMPT='0'))
                staged.rename(checkout)
            require_checkout(checkout, row)
    print(checkout, file=sys.stderr)
    return checkout


def install_repositories(names, manifest, dry_run, projects, offline, components, action='install'):
    """Resolve a complete install, reconfigure or removal plan before applying any owner.

    Parameters: names - converted owner names or None for defaults; manifest - validated owner profile; dry_run - preview only; projects - external parent; offline - forbid cloning; components - converted owner/component assignments or None; action - converted install/all/reconfigure/uninstall selector.
    Returns: None after exact owner commands have completed or been previewed.
    """
    print(f'names={names!r} manifest={manifest!r} dry_run={dry_run!r} projects={projects!r} offline={offline!r} components={components!r} action={action!r}', file=sys.stderr)
    if names is None:
        names = tuple(row['name'] for row in manifest if action == 'all' or row['default'])
    selected = validate_selection(names, manifest)
    choices = validate_component_assignments(components, selected)
    actions = []
    for row in selected:
        checkout = ensure_checkout(row, projects, offline, dry_run)
        profile_ids = (row.get('default_components') or None) if action == 'install' else None
        ids = choices.get(row['name'], profile_ids)
        owner_action = action
        if action == 'all' and ids is None and row['name'] == 'linux_programming_setup' and checkout.exists():
            ids = tuple(record['name'] for record in read_components(checkout, row))
        if action in ('uninstall', 'reconfigure') and ids is None:
            records = read_components(checkout, row)
            states = read_owner_states(checkout, row, records)
            ids = tuple(record['name'] for record in records if states.get(record['name'], False))
            if not ids:
                continue
        elif ids is not None and (checkout / row['installer']).is_file():
            validate_component_ids(ids, read_components(checkout, row))
        if action == 'all' and ids is not None:
            owner_action = 'install'
        actions.append((checkout, owner_action, ids, row))
    execute_actions(actions, dry_run)
    print(None, file=sys.stderr)


def require_single_owner(selected):
    """Require an unambiguous owner for an unqualified component selection.
    Parameters: selected - accepted repository records.
    Returns: None when exactly one owner is selected.
    """
    print(f'selected={selected!r}', file=sys.stderr)
    if len(selected) != 1:
        raise ValueError('unqualified --components requires exactly one selected repository')
    print(None, file=sys.stderr)


def parse_component_output(output):
    """Parse the tab-separated owner component protocol once.

    Parameters: output - raw component discovery stdout.
    Returns: named records with original fields, a converted default boolean and prerequisite IDs.
    """
    print(f'output={output!r}', file=sys.stderr)
    result = []
    for line in output.splitlines():
        fields = line.split('\t')
        if len(fields) < 3 or fields[2] not in ('on', 'off'):
            raise ValueError('owner returned malformed component metadata')
        identifier = parse_identifier(fields[0])
        result.append({'name': identifier, 'fields': fields, 'default': fields[2] == 'on', 'requires': tuple(fields[4].replace(',', ' ').split()) if len(fields) > 4 else ()})
    print(result, file=sys.stderr)
    return result


def read_components(checkout, row):
    """Query component definitions from the accepted external owner.
    Parameters: checkout - validated checkout path; row - accepted owner metadata.
    Returns: parsed named component records.
    """
    print(f'checkout={checkout!r}, row={row!r}', file=sys.stderr)
    output = query_owner(checkout, row, '--list-components')
    result = parse_component_output(output)
    validate_component_records(result)
    if row.get('default_components'):
        validate_component_ids(row['default_components'], result)
        for record in result:
            record['default'] = record['name'] in row['default_components']
    print(result, file=sys.stderr)
    return result


def run_owner_installer(command, checkout):
    """Run an owner action with child reboot requests suppressed.

    Parameters: command - prepared owner installer arguments; checkout - owner directory.
    Returns: None after the owner succeeds.
    """
    print(f'command={command!r} checkout={checkout!r}', file=sys.stderr)
    environment = dict(os.environ, INSTALLER_NO_REBOOT='1', ISC_NO_REBOOT='1')
    subprocess.run(command, cwd=checkout, check=True, env=environment)
    print(None, file=sys.stderr)


def owner_command(checkout, row, arguments, elevated=False):
    """Build an owner command with elevation when the operation needs root.

    Parameters: checkout - verified external checkout; row - selected owner with its environment; arguments - owner installer operands; elevated - whether this operation needs sudo.
    Returns: installer argv with reboot suppression and system receipts for sudo actions.
    """
    print(f'checkout={checkout!r} row={row!r} arguments={arguments!r} elevated={elevated!r}', file=sys.stderr)
    command = ['bash', str(checkout / 'install.sh'), *arguments]
    if row['name'] == 'linux_installations_setup' or elevated:
        command = ['sudo', '--', 'env', 'INSTALLER_NO_REBOOT=1', 'ISC_NO_REBOOT=1',
                   'ISC_RECEIPT_DIR=/var/lib/mt-stack/receipts', *command]
    elif row.get('environment'):
        command = ['env', *(f'{name}={value}' for name, value in row['environment'].items()), *command]
    print(command, file=sys.stderr)
    return command


def owner_action_commands(checkout, action, ids, row):
    """Separate the system Cursor package action from per-user editor setup.

    Parameters: checkout - verified external owner checkout; action - accepted lifecycle action; ids - selected component tuple or None; row - owner metadata.
    Returns: ordered argv lists for the selected owner.
    """
    print(f'checkout={checkout!r} action={action!r} ids={ids!r} row={row!r}', file=sys.stderr)
    if ids is None:
        commands = [owner_command(checkout, row, ['--all' if action == 'all' else '--default'])]
    else:
        flag = {'install': '--select', 'reconfigure': '--reconfigure', 'uninstall': '--uninstall'}[action]
        if row['name'] == 'linux_programming_setup' and 'cursor' in ids:
            package = owner_command(checkout, row, [flag, 'cursor'], elevated=True)
            remaining = tuple(component for component in ids if component != 'cursor')
            commands = [owner_command(checkout, row, [flag, ','.join(remaining)])] if remaining else []
            if action == 'uninstall':
                commands.append(package)
            else:
                commands.insert(0, package)
        else:
            commands = [owner_command(checkout, row, [flag, ','.join(ids)])]
    print(commands, file=sys.stderr)
    return commands


def operate_repository(name, projects, offline, dry_run, configure, manifest):
    """Open an owner's menu or print its component definitions.
    Parameters: name - parsed repository name; manifest - validated owner profile; projects - external parent; offline - forbid cloning; dry_run - preview only; configure - open the owner menu.
    Returns: None after a successful owner action or preview.
    """
    print(f'name={name!r}, manifest={manifest!r}, projects={projects!r}, offline={offline!r}, dry_run={dry_run!r}, configure={configure!r}', file=sys.stderr)
    row = validate_selection((name,), manifest)[0]
    checkout = ensure_checkout(row, projects, offline, dry_run)
    command = owner_command(checkout, row, []) if configure else ['bash', str(checkout / row['installer']), '--list-components']
    if dry_run:
        print(shlex.join(command))
    elif configure:
        run_owner_installer(command, checkout)
    else:
        for record in read_components(checkout, row):
            print('\t'.join(record['fields']))
    print(None, file=sys.stderr)


def validate_manifest(manifest, workstation):
    """Keep public links and workstation checkouts in separate profiles.
    Parameters: manifest - converted repository records; workstation - whether this is the opt-in local profile.
    Returns: None when every repository satisfies the migration boundary.
    """
    print(f'manifest={manifest!r} workstation={workstation!r}', file=sys.stderr)
    names = set()
    for row in manifest:
        name = row['name']
        if name in names or not name or Path(name).name != name or name in ('.', '..'):
            raise ValueError('invalid or duplicate repository name')
        names.add(name)
        if row.get('category') not in ('installer-support', 'linux-desktop', 'linux-development'):
            raise ValueError(f'{name}: only Linux setup-related projects belong here')
        if not workstation and (row.get('visibility') != 'public' or row.get('kind') != 'linked'):
            raise ValueError(f'{name}: private repository dependencies are not allowed')
        if row.get('source') != 'https://github.com/mikaeltorni/'+name:
            raise ValueError(f'{name}: source must be its canonical public repository URL')
        if row.get('installer') != 'install.sh' or (not workstation and (not row.get('branch') or not row.get('github_id'))):
            raise ValueError(f'{name}: missing owner installer or GitHub identity')
    if (ROOT / 'repositories').exists() or (ROOT / '.gitmodules').exists():
        raise ValueError('the hub must not contain project snapshots or Git submodules')
    print(None, file=sys.stderr)


def aggregate_checkouts(manifest, projects, offline, dry_run):
    """Resolve aggregate menu and query inputs in profile order.

    Parameters: manifest - validated owner profile; projects - external checkout parent; offline - forbid clones; dry_run - preview missing public checkouts.
    Returns: ordered owner and path pairs for required owners, available optional owners, and optional public owners when fetching.
    """
    print(f'manifest={manifest!r} projects={projects!r} offline={offline!r} dry_run={dry_run!r}', file=sys.stderr)
    require_external_path(projects)
    result = []
    for row in manifest:
        if row['kind'] == 'local' and not row['default'] and not (projects / row['name']).exists():
            if offline or not row['fetch_optional']:
                continue
        checkout = ensure_checkout(row, projects, offline, dry_run)
        result.append((row, checkout))
    print(result, file=sys.stderr)
    return result


def choose_repositories(manifest, projects, offline, dry_run):
    """Run the shared multi-repository component menu and build exact actions.

    Parameters: manifest - validated owner profile; projects - external checkout parent; offline - forbid clones; dry_run - preview actions and missing checkout paths.
    Returns: an owner action list, or None when the user cancels.
    """
    print(f'manifest={manifest!r} projects={projects!r} offline={offline!r} dry_run={dry_run!r}', file=sys.stderr)
    validate_menu_terminal()
    snapshots = []
    owners = {}
    for row, checkout in aggregate_checkouts(manifest, projects, offline, dry_run):
        records = read_owner_snapshot(checkout, row) if (checkout / row['installer']).is_file() else []
        owners[row['name']] = (row, checkout, records)
        snapshots.append({'name': row['name'], 'label': row['name'] + ' — ' + row['purpose'], 'enabled': row['default'], 'checkout': str(checkout), 'components': records})
    with tempfile.TemporaryDirectory(prefix='mt-stack-menu-') as directory:
        request = Path(directory) / 'request.json'
        reply = Path(directory) / 'reply.json'
        request.write_text(json.dumps(snapshots))
        subprocess.run(['bash', str(ROOT/'scripts/stack_menu.sh'), str(request), str(reply), '1' if dry_run else '0'], check=True)
        selection = parse_menu_output(reply.read_text())
    if selection is None:
        print(None, file=sys.stderr)
        return None
    actions = []
    validate_menu_selection(selection, owners)
    for name, enabled, install, uninstall in selection:
        if not enabled:
            continue
        row, checkout, records = owners[name]
        if uninstall:
            actions.append((checkout, 'uninstall', uninstall, row))
        if install or not uninstall:
            actions.append((checkout, 'install', install if records else None, row))
    print(actions, file=sys.stderr)
    return actions



def parse_component_assignment(text):
    """Convert one legacy or owner-qualified component assignment.

    Parameters: text - raw IDs or OWNER=IDs option value.
    Returns: an optional owner name and a converted component-ID tuple.
    """
    print(f'text={text!r}', file=sys.stderr)
    owner, separator, ids = text.partition('=')
    if separator:
        owner = parse_identifier(owner)
    value = ids if separator else text
    result = (owner if separator else None, parse_identifier_list(value, True))
    print(result, file=sys.stderr)
    return result


def validate_component_assignments(assignments, selected):
    """Require unambiguous, nonduplicate component choices for selected owners.

    Parameters: assignments - converted owner/ID tuples or None; selected - accepted repository rows.
    Returns: a mapping of explicitly configured owner names to unchanged ID tuples.
    """
    print(f'assignments={assignments!r} selected={selected!r}', file=sys.stderr)
    result = {}
    for owner, ids in assignments or ():
        if owner is None:
            require_single_owner(selected)
            owner = selected[0]['name']
        validate_selection((owner,), selected)
        if owner in result:
            raise ValueError('duplicate component assignment for ' + owner)
        result[owner] = ids
    print(result, file=sys.stderr)
    return result


def validate_component_ids(ids, records):
    """Accept a known component set, including an explicit core-only selection.

    Parameters: ids - converted component names; records - parsed owner metadata.
    Returns: the accepted IDs unchanged.
    """
    print(f'ids={ids!r} records={records!r}', file=sys.stderr)
    if ids:
        validate_selection(ids, records)
    print(ids, file=sys.stderr)
    return ids


def validate_action(action, ids):
    """Require a supported owner action and an explicit tuple for scoped maintenance.

    Parameters: action - converted install/all/reconfigure/uninstall selector; ids - converted component tuple or None.
    Returns: None when the action is well formed.
    """
    print(f'action={action!r} ids={ids!r}', file=sys.stderr)
    if action not in ('install', 'all', 'reconfigure', 'uninstall') or (action in ('reconfigure', 'uninstall') and ids is None) or (action == 'all' and ids is not None):
        raise ValueError('invalid owner action')
    print(None, file=sys.stderr)


def execute_actions(actions, dry_run):
    """Execute the same prepared owner actions for terminal and CLI selections.

    Parameters: actions - checkout/action/component/owner tuples; dry_run - print commands without executing.
    Returns: None after every requested command succeeds or is previewed.
    """
    print(f'actions={actions!r} dry_run={dry_run!r}', file=sys.stderr)
    for checkout, action, ids, row in actions:
        validate_action(action, ids)
    for checkout, action, ids, row in actions:
        for command in owner_action_commands(checkout, action, ids, row):
            print(shlex.join(command))
            if not dry_run:
                run_owner_installer(command, checkout)
    print(None, file=sys.stderr)


def validate_menu_terminal():
    """Require a terminal for the shared key-driven selection interface.

    Parameters: none.
    Returns: None when stdin and stdout are real terminals.
    """
    print('parameters=none', file=sys.stderr)
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ValueError('--menu requires a terminal; use --select for scripted installation')
    print(None, file=sys.stderr)


def parse_owner_states(output):
    """Convert owner installation-state rows once.

    Parameters: output - raw two-column installed/absent or legacy 1/0 protocol.
    Returns: a mapping of component IDs to installed booleans.
    """
    print(f'output={output!r}', file=sys.stderr)
    result = {}
    for line in output.splitlines():
        fields = line.split('\t')
        if len(fields) != 2 or fields[1] not in ('installed', 'absent', '1', '0'):
            raise ValueError('owner returned malformed detection metadata')
        result[fields[0]] = fields[1] in ('installed', '1')
    print(result, file=sys.stderr)
    return result


def read_owner_states(checkout, row, records):
    """Read and validate installation state against the owner's known component set.

    Parameters: checkout - accepted owner checkout; row - registry metadata; records - converted component records.
    Returns: a mapping of known component IDs to installed booleans.
    """
    print(f'checkout={checkout!r} row={row!r} records={records!r}', file=sys.stderr)
    result = parse_owner_states(query_owner(checkout, row, '--detect'))
    validate_component_ids(tuple(result), records)
    print(result, file=sys.stderr)
    return result


def query_repositories(mode, projects, offline, dry_run, manifest):
    """Inspect every linked owner without executing any installation action.

    Parameters: mode - converted detect/export selector; manifest - registry metadata; projects - external checkout parent; offline - forbid cloning; dry_run - preserve clone preview behavior.
    Returns: formatted owner/component states or a shared master configuration JSON document.
    """
    print(f'mode={mode!r} manifest={manifest!r} projects={projects!r} offline={offline!r} dry_run={dry_run!r}', file=sys.stderr)
    lines = []
    document = {'schema_version': 1, 'scope': 'master', 'repos': {}}
    for row, checkout in aggregate_checkouts(manifest, projects, offline, dry_run):
        records = read_components(checkout, row)
        if mode == 'detect':
            states = read_owner_states(checkout, row, records)
            lines.extend(row['name'] + '\t' + record['name'] + '\t' + ('installed' if states.get(record['name'], False) else 'absent') for record in records)
        else:
            document['repos'][row['name']] = {'enabled': int(row['default']), 'components': {record['name']: {'on': int(record['default']), 'uninstall': 0} for record in records}}
    result = '\n'.join(lines) if mode == 'detect' else json.dumps(document, indent=2, sort_keys=True)
    print(result, file=sys.stderr)
    return result


def validate_query_result(result, optional):
    """Require successful metadata reads, allowing unsupported optional queries.

    Parameters: result - completed owner query; optional - permit unavailable optional metadata.
    Returns: raw stdout on success or empty text for an unsupported optional query.
    """
    print(f'result={result!r} optional={optional!r}', file=sys.stderr)
    if result.returncode and not optional:
        raise ValueError('owner metadata query failed: ' + result.stderr.strip())
    value = result.stdout if result.returncode == 0 else ''
    print(value, file=sys.stderr)
    return value


def query_owner(checkout, row, flag, optional=False):
    """Read one owner protocol without sourcing its implementation.

    Parameters: checkout - accepted external owner; row - registry metadata; flag - metadata query; optional - accept unsupported optional metadata.
    Returns: the validated raw owner reply.
    """
    print(f'checkout={checkout!r} row={row!r} flag={flag!r} optional={optional!r}', file=sys.stderr)
    environment = dict(os.environ, **row.get('environment', {}))
    reply = subprocess.run(['bash', str(checkout/row['installer']), flag], cwd=checkout,
                           text=True, capture_output=True, env=environment)
    result = validate_query_result(reply, optional)
    print(result, file=sys.stderr)
    return result


def parse_configurable_output(output):
    """Convert configurable component identifiers from an owner query.

    Parameters: output - newline-separated owner IDs.
    Returns: a tuple of unchanged identifiers.
    """
    print(f'output={output!r}', file=sys.stderr)
    result = tuple(output.splitlines())
    print(result, file=sys.stderr)
    return result


def read_owner_snapshot(checkout, row):
    """Read component choices, installed state and optional configuration routing.

    Parameters: checkout - accepted external owner; row - registry metadata.
    Returns: parsed component dictionaries suitable for the shared menu.
    """
    print(f'checkout={checkout!r} row={row!r}', file=sys.stderr)
    records = read_components(checkout, row)
    states = read_owner_states(checkout, row, records)
    configure = parse_configurable_output(query_owner(checkout, row, '--list-configurable-components', True))
    validate_component_ids(configure, records)
    for record in records:
        record['installed'] = states.get(record['name'], False)
        record['configure'] = record['name'] in configure
    print(records, file=sys.stderr)
    return records


def parse_menu_output(output):
    """Convert the shared menu's explicit action document once.

    Parameters: output - raw JSON reply from the menu bridge.
    Returns: converted owner/enable/install/remove tuples, or None on cancellation.
    """
    print(f'output={output!r}', file=sys.stderr)
    document = json.loads(output)
    if document.get('cancelled'):
        print(None, file=sys.stderr)
        return None
    result = tuple((row['name'], row['enabled'], tuple(row['install']), tuple(row['uninstall'])) for row in document['repositories'])
    print(result, file=sys.stderr)
    return result


def validate_menu_selection(selection, owners):
    """Require exact known owners and disjoint accepted component actions.

    Parameters: selection - converted menu tuples; owners - accepted owner metadata/checkouts/components.
    Returns: None after every selected action has passed validation.
    """
    print(f'selection={selection!r} owners={owners!r}', file=sys.stderr)
    validate_selection(tuple(row[0] for row in selection), [value[0] for value in owners.values()])
    for name, enabled, install, uninstall in selection:
        if not isinstance(enabled, bool):
            raise ValueError('menu returned an invalid enabled state')
        records = owners[name][2]
        validate_component_ids(install, records)
        validate_component_ids(uninstall, records)
        if set(install) & set(uninstall):
            raise ValueError('menu cannot install and remove the same component')
    print(None, file=sys.stderr)


def validate_component_records(records):
    """Require unique component IDs and owner-local prerequisite references.

    Parameters: records - converted component metadata.
    Returns: None when identifiers and all prerequisites are consistent.
    """
    print(f'records={records!r}', file=sys.stderr)
    validate_component_ids(tuple(row['name'] for row in records), records)
    for row in records:
        validate_component_ids(row['requires'], records)
    print(None, file=sys.stderr)


def inspect_registry(mode, manifest):
    """Build the selected profile's list or architecture report.

    Parameters: mode - parsed list/check selector; manifest - converted repository records.
    Returns: the validated, formatted registry report.
    """
    print(f'mode={mode!r} manifest={manifest!r}', file=sys.stderr)
    profile = 'local workstation checkouts' if manifest and manifest[0]['kind'] == 'local' else 'public Linux setup links'
    result = f'PASS: {profile} and external repository architecture' if mode == 'check' else '\n'.join(row['name'] + '\t' + row['purpose'] for row in manifest)
    print(result, file=sys.stderr)
    return result


def apply_stack_request(interface, owners, dry_run, projects, offline, components, action, manifest):
    """Execute an accepted menu or CLI request through the same action operations.

    Parameters: interface - menu/auto/cli selector; owners - converted owner tuple; dry_run - preview actions; projects - resolved checkout parent; offline - forbid cloning; components - converted component assignments; action - install/all/reconfigure/uninstall selector; manifest - repository registry.
    Returns: None after completion or cancellation.
    """
    print(f'interface={interface!r} owners={owners!r} dry_run={dry_run!r} projects={projects!r} offline={offline!r} components={components!r} action={action!r} manifest={manifest!r}', file=sys.stderr)
    if interface == 'menu' or (interface == 'auto' and sys.stdin.isatty()):
        actions = choose_repositories(manifest, projects, offline, dry_run)
        if actions is not None:
            execute_actions(actions, dry_run)
    else:
        install_repositories(owners, manifest, dry_run, projects, offline, components, action)
    print(None, file=sys.stderr)


def main(arguments):
    """Route converted options to registry queries or shared lifecycle operations.
    Parameters: arguments - raw command line arguments.
    Returns: zero for successful queries or actions, two for rejected or failed operations.
    """
    print(f'arguments={arguments!r}', file=sys.stderr)
    selector, converted, profile = parse_arguments(arguments)
    try:
        manifest = load_manifest(*profile)
        if selector == 'owner':
            operate_repository(*converted, manifest)
        elif selector == 'query':
            result = query_repositories(*converted, manifest)
            print(result)
        elif selector == 'registry':
            result = inspect_registry(*converted, manifest)
            print(result)
        elif selector == 'apply':
            apply_stack_request(*converted, manifest)
    except (ValueError, argparse.ArgumentTypeError, OSError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        print(2, file=sys.stderr)
        return 2
    print(0, file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
