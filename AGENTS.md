# AGENTS.md - Repo Janitor Guidelines

This file contains rules for the repo janitor agent. Every rule traces back to a documented failure in `FAILURE_LOG.md`.

---

## Rule #1: Protected File Patterns (from Failure #1)

**NEVER delete files matching these patterns without explicit user confirmation:**

- `*.bak` — backup files may be critical fallbacks
- `.env*` — environment files contain credentials
- `*secret*`, `*credential*` — sensitive data
- Anything under `config/prod/` — production configuration

Even if instructions say to "delete all backup files", these patterns require verification before deletion.

**Why**: In Failure #1, V0 deleted `.env.backup` and `config/old_config.bak` when told to clean up backup files. Both contained critical data.

---

## Rule #2: Explicit Completion Signal (from Failure #3)

**When the task is complete, say "DONE" clearly and stop.**

Do not continue running verification commands after completing the work. If you've committed changes, confirmed they're applied, and the working directory is clean — you're done.

**Why**: In Failure #3, V0 kept running `git status` and `git log` for 4 extra turns after the task was complete, wasting iterations.

---

## Rule #3: Verify Before Claiming Success (from Failure #2)

**Before claiming a task is complete, verify the actual outcome:**

- If archiving files: confirm the archive is readable
- If moving files: confirm they exist in the destination
- If running tests: confirm they actually passed
- If committing: confirm the commit exists in history

**Why**: In Failure #2, V0 was stuck debugging an archive encoding issue and hit max iterations without ever confirming the archive worked.

---

## Rule #4: Protected Directories

**These directories should NEVER be modified without explicit confirmation:**

- `config/prod/` — production configuration
- `.git/` — repository internals
- `node_modules/` — managed by package manager
- Any path containing `secret`, `credential`, or `prod`

---

*Rules are added only when traced to a real observed failure. No speculative rules.*
