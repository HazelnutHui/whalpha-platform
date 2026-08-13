# Node.js Toolchain Provisioning

## Purpose

This document records the prepared Node.js toolchain provisioning procedure for `dell5820`. The goal is to install the system Node.js and npm toolchain required to verify the React/TypeScript/Vite frontend scaffold.

## Status

Prepared, Not Applied

Codex prepared and validated the guarded provisioning script, but did not apply it because passwordless sudo is not available in the current session.

## Approved Version

- Node.js 24 LTS
- npm version provided by the Node.js 24 package

## Why Node.js 24 LTS

Node.js 24 LTS is the approved frontend development runtime for this project. It is current enough for the accepted Vite/React/TypeScript scaffold while avoiding non-LTS Current releases.

## Why Not Node.js 26 Current

Node.js 26 Current is not selected because this project should use an LTS runtime for a stable development foundation.

## Installation Source

The prepared script uses the NodeSource `node_24.x` DEB repository with a dedicated APT source list and dedicated keyring.

It does not use the NodeSource setup script pipe pattern.

## Safety Model

The script:

- defaults to dry-run
- requires the single explicit `--apply` argument for system modification
- requires root for apply mode
- verifies `hostname=dell5820`
- verifies Ubuntu 24.04 series
- verifies `amd64` architecture
- checks `apt-get`, `curl`, `gpg`, and `dpkg`
- checks dpkg state before changes
- refuses unknown Node/npm installations
- refuses conflicting NodeSource repository or keyring files
- creates a dedicated source list and keyring only after preflight passes
- does not run `apt upgrade`, `apt full-upgrade`, `apt autoremove`, or global npm install
- does not modify shell profiles
- does not install project dependencies

## Dry-Run

```bash
cd /home/hui/projects/trading-intelligence-platform
sudo scripts/admin/provision-node-toolchain.sh
```

Dry-run does not require root behavior from the script itself, but running it with sudo is acceptable for matching the final operator workflow. It must not create repository files, run `apt-get update`, or install packages.

## Apply

```bash
cd /home/hui/projects/trading-intelligence-platform
sudo scripts/admin/provision-node-toolchain.sh --apply
```

Apply mode installs the NodeSource repository and `nodejs` package after preflight passes.

## Verification

After apply, verify:

```bash
node --version
npm --version
command -v node
command -v npm
dpkg-query -W -f='${Package}|${Version}|${Architecture}|${Status}
' nodejs
apt-cache policy nodejs
npm config get prefix
npm config get registry
```

Node major version must be 24.

## Re-run Behavior

The script should tolerate an already completed expected Node.js 24 installation, but it must stop on unknown Node versions, unknown package ownership, or unexpected repository/keyring files.

## Failure Handling

The script does not uninstall packages, delete existing repository files, or perform rollback. If installation partially succeeds, inspect the system state manually before continuing.

## Files Added to the System

When applied successfully, the script may add:

- `/etc/apt/keyrings/nodesource-node24.gpg`
- `/etc/apt/sources.list.d/nodesource-node24.list`

No key contents are stored in Git.

## Removal Is Not Automated

Removal of Node.js or the NodeSource repository is intentionally not automated by this project script.

## Project Dependency Installation

After Node.js 24 and npm are verified, install frontend dependencies from the project directory:

```bash
cd /home/hui/projects/trading-intelligence-platform/apps/web
npm install --save-exact=false
npm run build
```

This step has not been executed yet.

## Documentation Checkpoint

After successful apply and frontend verification, update current status, infrastructure, local development instructions, roadmap, open questions, and changelog.
