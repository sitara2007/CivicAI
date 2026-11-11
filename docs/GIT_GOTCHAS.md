## Troubleshooting: Embedded Git Repositories

**Problem:** `warning: adding embedded git repository`

**Cause:** Running `git init` inside a subfolder creates a nested Git repository.

**Fix:** From the monorepo root, untrack the folder, remove its inner `.git` directory, then add it again:

```bash
git rm --cached <folder>
rm -rf <folder>/.git
git add <folder>
```

**Prevention:** Never run `git init` inside a monorepo.
