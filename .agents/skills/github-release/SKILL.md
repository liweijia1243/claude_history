---
name: github-release
description: Use when the user asks Codex to publish a GitHub release for this project with a semantic version such as 0.1.3.
---

# GitHub Release

Run this repository's release workflow. The version must come from the user's request, for example `$github-release 0.1.3` or "使用 github-release 发布 0.1.3".

## Preconditions

1. Extract the version and validate it is exactly `x.y.z` numeric semver, without a leading `v`.
2. Stop and ask for a valid version if the version is missing or invalid.
3. Check whether `v{version}` already exists with `git tag -l "v{version}"`; stop if it exists.
4. Use approvals for network, push, release creation, and other privileged operations when required by the current Codex environment.

## Workflow

### 1. Commit Existing Work

Run `git status`.

If there are changes:
- Inspect `git diff --stat` and `git diff`.
- Create a concise Chinese commit message that matches the repository's existing commit style.
- Stage only relevant files.
- Commit the changes.

If the worktree is clean, skip this step.

### 2. Sync To Main

Check the current branch with `git branch --show-current`.

If already on `main`:
- Push `main` with `git push origin main`.

If on another branch:
1. Record the branch name.
2. Switch to `main`.
3. Find commits not on `main` with `git log main..{branch} --oneline`.
4. Cherry-pick the branch's release-relevant commits onto `main`.
5. Push `main` with `git push origin main`.
6. Continue the rest of the workflow on `main`; do not switch back unless the user asks.

### 3. Update Version Files

Update all release version references:

- `build_deb.sh`: `VERSION="x.y.z"` -> `VERSION="{version}"`
- `deb_package/DEBIAN/control`: `Version: x.y.z` -> `Version: {version}`
- `build_pkg.sh`: `VERSION="x.y.z"` -> `VERSION="{version}"`

### 4. Commit Version Bump

Run:

```bash
git add build_deb.sh deb_package/DEBIAN/control build_pkg.sh
git commit -m "chore: 发布版本升至 v{version}"
```

### 5. Tag And Push

Run:

```bash
git tag v{version}
git push origin main
git push origin v{version}
```

### 6. Build Local Package

Build for the current OS:

```bash
if [ "$(uname)" = "Darwin" ]; then
    bash build_pkg.sh
else
    bash build_deb.sh
fi
```

If the build fails, stop and report the failure.

### 7. Generate Release Notes

1. Find the previous tag with `git describe --tags --abbrev=0 HEAD^`.
2. Collect changes with `git log {previous_tag}..HEAD --oneline`.
3. Summarize changes by category in Chinese.
4. Use this structure:

```markdown
## What's New

### 功能改进
- ...

### Bug 修复
- ...

---

### 安装

**Ubuntu/Debian:**
sudo dpkg -i claude-history_{version}_amd64.deb
sudo apt-get install -f
claude_history

**macOS:**
sudo installer -pkg claude-history_{version}_arm64.pkg -target /
claude_history

> 支持 Ubuntu 20.04+ 和 macOS (Apple Silicon)，启动后自动在浏览器中打开 http://localhost:8787
```

### 8. Create GitHub Release

Collect built assets from the repository root:

```bash
ASSETS=""
[ -f claude-history_{version}_amd64.deb ] && ASSETS+="claude-history_{version}_amd64.deb "
[ -f claude-history_{version}_arm64.pkg ] && ASSETS+="claude-history_{version}_arm64.pkg "
```

Create the release:

```bash
gh release create v{version} $ASSETS --title "v{version}" --notes "{release_note}"
```

Report the release URL when complete.
