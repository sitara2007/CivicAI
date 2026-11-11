# Git Gotchas

## 1. Embedded Git Repositories (The Submodule Trap)
**Problem:** `warning: adding embedded git repository`.
**Cause:** You ran `git init` inside a subfolder (like `benchmark/`) and then tried to add it to the main repo.
**Fix:**
1. `git rm --cached <folder>`
2. `rm -rf <folder>/.git`
3. `git add <folder>/`
**Prevention:** Never run `git init` inside a monorepo unless you are creating a proper Git Submodule.

## 2. Non-Fast-Forward Push Error (After Rebase)
**Problem:** `! [rejected] main -> main (non-fast-forward)`.
**Cause:** You ran `git pull --rebase`, which rewrote your local commit history (changed commit hashes). The remote branch still has the old history.
**Fix:** `git push --force-with-lease origin <branch-name>`
**Prevention:** NEVER use `git push -f`. ALWAYS use `--force-with-lease` to ensure you don't overwrite a teammate's work.
