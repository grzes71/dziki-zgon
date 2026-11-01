---
description: Create or checkout branch (optional), stage, commit using Conventional Commits in English, and push to remote repository
---

Execute the procedure to commit and push changes to the remote repository:

> **Parameter**: `<branch name>` is **optional** (e.g. `/git-push` or `/git-push feat/branch-name`). If not specified, use the current active branch.

1. **Determine Target Branch**:
   Check the current branch using `git branch --show-current`:
   - If a `<branch name>` parameter was provided and differs from the current branch:
     - Check if it exists or switch/create:
       ```bash
       git checkout -B <branch name>
       ```
       *(or `git checkout -b <branch name>` if creating new, or `git checkout <branch name>` if switching)*.
   - If no `<branch name>` was provided:
     - Continue on the current active branch.

2. **Formulate Commit Message (Conventional Commits ONLY)**:
   Check modified files using `git status` and read the latest entry from `HISTORY.md`. Formulate a commit message strictly adhering to the **Conventional Commits** specification in English:
   - Structure: `<type>(<scope>): <concise imperative description in English>` (scope is optional, e.g. `<type>: <description>`)
   - Allowed types: `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `chore`, `ci`, `build` (append `!` for breaking changes, e.g. `feat!: ...`)
   - Examples:
     - `feat(gameover): update victory and defeat poems`
     - `fix(collision): resolve player boundary check`
     - `chore(texts): bump version in scroll.txt`

3. **Stage All Changes**:
   ```bash
   git add .
   ```

4. **Commit the Changes**:
   ```bash
   git commit -m "<type>(<optional-scope>): <concise description in English>"
   ```

5. **Push to Remote with Upstream**:
   ```bash
   git push -u origin <branch name>
   ```
   *(where `<branch name>` is the target branch or current active branch)*.

6. **Confirmation**:
   Confirm successful execution to the user, specifying the target branch, commit hash, and commit message.
