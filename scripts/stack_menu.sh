#!/usr/bin/env bash
# Route parsed hub metadata through the shared framework's real aggregate menu.
set -euo pipefail
STACK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$STACK_ROOT/.installer-support/bootstrap.sh"
isc_load_menu
declare -A STACK_CHECKOUTS
STACK_MENU_DRY_RUN="${3:-0}"
while IFS= read -r -d '' kind && IFS= read -r -d '' key && IFS= read -r -d '' value; do
  case "$kind" in
    repo) CM_REPOS+=("$key"); CM_REPO_LABEL["$key"]="$value" ;;
    checkout) STACK_CHECKOUTS["$key"]="$value" ;;
    enabled) CM_REPO_ENABLED["$key"]="$value" ;;
    ids) CM_COMP_IDS["$key"]="$value" ;;
    label) CM_COMP_LABEL["$key"]="$value" ;;
    selected) CM_COMP_ON["$key"]="$value" ;;
    installed) CM_COMP_INSTALLED["$key"]="$value" ;;
    configure) CM_COMP_CONFIGURE_ELIGIBLE["$key"]="$value" ;;
    requires) CM_COMP_REQUIRES["$key"]="$value" ;;
    section) CM_COMP_SECTION["$key"]="$value" ;;
  esac
done < <(python3 - "$1" <<'PY'
import json,sys
for row in json.load(open(sys.argv[1])):
    values=[('repo',row['name'],row['label']),('checkout',row['name'],row['checkout']),('enabled',row['name'],str(int(row['enabled']))),('ids',row['name'],' '.join(item['name'] for item in row['components']))]
    for item in row['components']:
        key=row['name']+'|'+item['name']
        values.extend([('label',key,item['fields'][1]),('selected',key,str(int(item['default'] and not item['installed']))),('installed',key,str(int(item['installed']))),('configure',key,str(int(item['configure']))),('requires',key,' '.join(item['requires'])),('section',key,item['fields'][3] if len(item['fields'])>3 else '')])
    for kind,key,value in values:
        sys.stdout.buffer.write((kind+'\0'+key+'\0'+value+'\0').encode())
PY
)
# Open the owning repository's existing detail screen; never source owner code.
# Parameters: repo - accepted owner identifier; id - its configurable component.
# Returns: the owner detail command's exit status.
stack_configure_component() {
  printf 'repo=%s id=%s\n' "$1" "$2" >&2
  local repo="$1" id="$2" status=0
  if [[ "$STACK_MENU_DRY_RUN" == 1 ]]; then
    printf '%q ' bash "${STACK_CHECKOUTS[$repo]}/install.sh" --configure-component "$id"
    printf '\n0\n' >&2
    return 0
  fi
  (cd "${STACK_CHECKOUTS[$repo]}" && bash ./install.sh --configure-component "$id") || status=$?
  printf '%s\n' "$status" >&2
  return "$status"
}
CM_CONFIGURE_CALLBACK=stack_configure_component
for repo in "${CM_REPOS[@]}"; do cm_reconcile_dependencies "$repo"; done
if ! cm_aggregate_menu; then
  printf '{"cancelled":true}\n' > "$2"
  exit 0
fi
{
  for repo in "${CM_REPOS[@]}"; do
    apply=() remove=()
    for id in ${CM_COMP_IDS[$repo]:-}; do
      if [[ "${CM_COMP_UNINSTALL[$repo|$id]:-0}" == 1 ]]; then remove+=("$id")
      elif [[ "${CM_COMP_ON[$repo|$id]:-0}" == 1 ]]; then apply+=("$id"); fi
    done
    printf '%s\0%s\0%s\0%s\0' "$repo" "${CM_REPO_ENABLED[$repo]:-0}" "$(IFS=,; printf '%s' "${apply[*]}")" "$(IFS=,; printf '%s' "${remove[*]}")"
  done
} | python3 -c 'import json,sys; values=sys.stdin.buffer.read().decode().split("\0")[:-1]; rows=[dict(name=values[i],enabled=values[i+1]=="1",install=values[i+2].split(",") if values[i+2] else [],uninstall=values[i+3].split(",") if values[i+3] else []) for i in range(0,len(values),4)]; json.dump(dict(cancelled=False,repositories=rows),open(sys.argv[1],"w"))' "$2"
