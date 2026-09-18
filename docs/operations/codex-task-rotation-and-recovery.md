# Codex Task Rotation and Recovery

## Purpose

Use this checklist to move a long-running project to a fresh Codex task without
using chat memory as project state or disturbing workstation data, GitHub, or
the public website.

## Close the current task

1. Finish the current bounded operation, or record its exact process owner,
   command, checkpoint, restart behavior, and stop conditions.
2. Verify there is no unexplained writer, staging directory, partial package,
   listener, failed service, or unresolved deployment.
3. Reconcile `git status`, branch, HEAD, remotes, ignored private paths, and all
   intended changes. Run secret and large-file checks before any public push.
4. Exact-reread the current authoritative data packages and record only their
   necessary identities and limitations in `current-context.md` or a dated
   audit.
5. Replace superseded facts in `current-context.md`, `current-status.md`, and
   `current-work.md`. Do not append a chat narrative to those files.
6. Update routed ADRs, contracts, operations, indexes, and one concise changelog
   milestone. Keep historical detail in dated audits.
7. Run proportionate backend/frontend tests, build the website, and complete
   deployment postflight if deployment is in scope.
8. Commit the reconciled checkpoint. Push only reviewed code, documentation,
   tests, and safe small artifacts; never push credentials or private data.

## Open the new task

The first turn is read-only and must:

1. read `AGENTS.md`, root `README.md`, `docs/README.md`,
   `docs/project/current-context.md`, `docs/project/current-status.md`, and
   `docs/project/current-work.md` in that order;
2. read only the routed ADRs/contracts/operations named by `current-work.md`;
3. verify host/user, canonical repository, branch, HEAD, worktree, remotes, and
   any active or residual processes;
4. verify the exact current data-package identities and permission boundaries
   without reading credentials or sensitive raw content;
5. verify the served release, local bundle evidence, listener/service state,
   and repository-to-Production mapping when deployment state matters;
6. compare actual evidence with all three current documents; and
7. report `CONTEXT_RECONCILED`, `CONTEXT_RECONCILED_WITH_DISCREPANCIES`, or
   `CONTEXT_NOT_RECONCILED` before material changes.

## Guardrails

- Do not paste the complete prior chat into the new task.
- A short handoff may state the repository path, expected checkpoint commit,
  active objective, and instruction to run this recovery procedure.
- A process observed in an old task is not assumed alive; verify it.
- A completed package is not assumed authoritative; exact-reread it.
- A website statement is not data authority; verify its source contract.
- Switching tasks grants no new network, data-write, deployment, Git push,
  credential, or research-stage authority.
