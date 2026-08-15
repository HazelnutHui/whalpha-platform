#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "${script_dir}/../.." && pwd)
bundle_root="${repo_root}/build/oci-dashboard"
remote_alias="whalpha-oci"

usage() {
  cat <<MSG
Usage: $0 --bundle-release RELEASE_ID [--dry-run]
       $0 --bundle-release RELEASE_ID --apply

Default is dry-run. This script is reviewed for future deployment, but this round must not run --apply.
MSG
}

bundle_release=""
apply="false"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --bundle-release)
      bundle_release="${2:-}"
      shift 2
      ;;
    --dry-run)
      apply="false"
      shift
      ;;
    --apply)
      apply="true"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "${bundle_release}" ]]; then
  echo "--bundle-release is required" >&2
  usage >&2
  exit 2
fi
if [[ ! "${bundle_release}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}Z-[0-9a-f]{7,40}$ ]]; then
  echo "Unsafe bundle release id" >&2
  exit 2
fi

cd "${repo_root}"
[[ "$(hostname)" == "dell5820" ]] || { echo "must run on dell5820" >&2; exit 1; }
[[ "$(whoami)" == "hui" ]] || { echo "must run as hui" >&2; exit 1; }
[[ "$(git branch --show-current)" == "main" ]] || { echo "must run on main" >&2; exit 1; }
[[ -z "$(git status --short)" ]] || { echo "working tree must be clean" >&2; exit 1; }

bundle_dir="${bundle_root}/${bundle_release}"
[[ -f "${bundle_dir}/deployment-manifest.json" ]] || { echo "bundle manifest missing" >&2; exit 1; }
(cd "${bundle_dir}" && sha256sum -c checksums.sha256 >/dev/null)

echo "mode=$([[ "${apply}" == "true" ]] && echo apply || echo dry-run)"
echo "bundle_release=${bundle_release}"
echo "remote_alias=${remote_alias}"

ssh "${remote_alias}" 'hostname && whoami && nginx -v 2>&1 || true && test -f /etc/nginx/auth/whalpha-dashboard.htpasswd && echo htpasswd_present || echo htpasswd_missing'

if [[ "${apply}" != "true" ]]; then
  echo "dry_run_only=true"
  exit 0
fi

echo "Apply mode is intentionally not implemented for this reviewed preparation step." >&2
exit 3
