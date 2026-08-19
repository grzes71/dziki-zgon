import re
import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple, Dict

CONVENTIONAL_COMMIT_REGEX = re.compile(
    r"^(?P<type>[a-zA-Z0-9_-]+)(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?:\s*(?P<desc>.+)$"
)

def parse_commit_message(message: str) -> Optional[Dict[str, any]]:
    """
    Parses a commit message or PR title according to Conventional Commits.
    Returns a dict with keys: type, scope, breaking, desc, raw, is_breaking
    """
    if not message:
        return None
    
    lines = [line.strip() for line in message.strip().splitlines() if line.strip()]
    if not lines:
        return None
        
    first_line = lines[0]
    match = CONVENTIONAL_COMMIT_REGEX.match(first_line)
    if not match:
        return None
        
    c_type = match.group("type").lower()
    scope = match.group("scope")
    breaking_marker = bool(match.group("breaking"))
    desc = match.group("desc")
    
    # Check for BREAKING CHANGE in message body/footer
    has_breaking_body = any(
        line.startswith("BREAKING CHANGE:") or line.startswith("BREAKING-CHANGE:")
        for line in lines[1:]
    )
    is_breaking = breaking_marker or has_breaking_body
    
    return {
        "type": c_type,
        "scope": scope,
        "desc": desc,
        "is_breaking": is_breaking,
        "raw": first_line,
        "body": "\n".join(lines[1:]) if len(lines) > 1 else ""
    }

def determine_bump_type(parsed_commits: List[Dict[str, any]]) -> Optional[str]:
    """
    Determines whether a bump is 'major', 'minor', 'patch', or None.
    Priority: major > minor > patch > None.
    """
    has_major = False
    has_minor = False
    has_patch = False
    
    for c in parsed_commits:
        if not c:
            continue
        if c["is_breaking"]:
            has_major = True
        elif c["type"] == "feat":
            has_minor = True
        elif c["type"] in ("fix", "perf", "bugfix"):
            has_patch = True
            
    if has_major:
        return "major"
    if has_minor:
        return "minor"
    if has_patch:
        return "patch"
    return None

def parse_semver(tag: str) -> Tuple[int, int, int]:
    """
    Parses a git tag like 'v1.2.3' or '1.2.3' into (major, minor, patch).
    """
    clean_tag = tag.lstrip("v").strip()
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", clean_tag)
    if not match:
        raise ValueError(f"Invalid semver tag: {tag}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))

def get_latest_git_tag(cwd: Optional[Path] = None) -> Optional[str]:
    """
    Finds the latest semver tag in the repository.
    """
    try:
        res = subprocess.run(
            ["git", "tag", "-l", "v*"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        tags = [t.strip() for t in res.stdout.splitlines() if t.strip()]
        if not tags:
            return None
            
        valid_tags = []
        for t in tags:
            try:
                ver = parse_semver(t)
                valid_tags.append((ver, t))
            except ValueError:
                continue
                
        if not valid_tags:
            return None
            
        valid_tags.sort(key=lambda item: item[0])
        return valid_tags[-1][1]
    except Exception:
        return None

def get_pr_commit_messages(merge_sha: Optional[str]) -> List[str]:
    """
    Returns the commit messages introduced by the merged PR, using its merge
    commit. This avoids analyzing an arbitrary window of the target branch.

    - For a merge commit (two parents), `merge_sha^1..merge_sha` lists exactly
      the commits brought in by the PR.
    - For squash/rebase merges (one parent) the merge commit itself is the PR
      commit, so we fall back to that single message.
    """
    if not merge_sha:
        return []

    messages = []
    try:
        res = subprocess.run(
            ["git", "log", "--format=%B%x1e", f"{merge_sha}^1..{merge_sha}"],
            capture_output=True,
            text=True
        )
        if res.returncode == 0:
            messages = [c.strip() for c in res.stdout.split("\x1e") if c.strip()]
    except Exception:
        messages = []

    if not messages:
        try:
            res = subprocess.run(
                ["git", "log", "-n", "1", "--format=%B", merge_sha],
                capture_output=True,
                text=True
            )
            if res.returncode == 0 and res.stdout.strip():
                messages = [res.stdout.strip()]
        except Exception:
            messages = []

    return messages

def compute_next_version(latest_tag: Optional[str], bump_type: str) -> str:
    """
    Computes the next tag given the latest tag and bump type ('major', 'minor', 'patch').
    """
    if not latest_tag:
        if bump_type == "major":
            return "v1.0.0"
        elif bump_type == "minor":
            return "v0.1.0"
        else: # patch
            return "v0.0.1"
            
    major, minor, patch = parse_semver(latest_tag)
    
    if bump_type == "major":
        return f"v{major + 1}.0.0"
    elif bump_type == "minor":
        return f"v{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"v{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Unknown bump type: {bump_type}")

def generate_changelog(
    parsed_commits: List[Dict[str, any]],
    pr_number: Optional[int] = None,
    pr_author: Optional[str] = None,
    pr_url: Optional[str] = None
) -> str:
    """
    Generates a Markdown changelog categorized by commit type.
    """
    breaking_items = []
    features = []
    fixes = []
    perfs = []
    others = []
    
    for c in parsed_commits:
        if not c:
            continue
        scope_prefix = f"**{c['scope']}:** " if c.get("scope") else ""
        item_text = f"- {scope_prefix}{c['desc']}"
        
        if c["is_breaking"]:
            breaking_items.append(item_text)
        elif c["type"] == "feat":
            features.append(item_text)
        elif c["type"] in ("fix", "bugfix"):
            fixes.append(item_text)
        elif c["type"] == "perf":
            perfs.append(item_text)
        else:
            others.append(item_text)
            
    sections = []
    if breaking_items:
        sections.append("### 💥 Breaking Changes\n" + "\n".join(breaking_items))
    if features:
        sections.append("### 🚀 Nowości (Features)\n" + "\n".join(features))
    if fixes:
        sections.append("### 🐛 Poprawki (Bug Fixes)\n" + "\n".join(fixes))
    if perfs:
        sections.append("### ⚡ Wydajność (Performance)\n" + "\n".join(perfs))
    if others and not (features or fixes or perfs or breaking_items):
        sections.append("### 🔧 Inne zmiany\n" + "\n".join(others))
        
    if pr_number and pr_url:
        author_str = f" przez @{pr_author}" if pr_author else ""
        sections.append(f"\n*Pull Request: [#{pr_number}]({pr_url}){author_str}*")
        
    return "\n\n".join(sections).strip()

def process_github_pr_event(event_data: dict, git_commits: Optional[List[str]] = None) -> Dict[str, any]:
    """
    Analyzes a GitHub pull_request closed event and returns release metadata.
    """
    pr = event_data.get("pull_request", {})
    if not pr.get("merged", False):
        return {"should_release": False, "reason": "PR not merged"}
        
    pr_title = pr.get("title", "")
    pr_body = pr.get("body", "") or ""
    pr_number = pr.get("number")
    pr_url = pr.get("html_url")
    pr_author = pr.get("user", {}).get("login")
    
    # Collect candidates: PR title + body, and any git commit messages
    candidates = [f"{pr_title}\n\n{pr_body}"]
    if git_commits:
        candidates.extend(git_commits)
        
    parsed_commits = []
    for raw_msg in candidates:
        p = parse_commit_message(raw_msg)
        if p:
            # Deduplicate by raw description
            if not any(existing["desc"] == p["desc"] for existing in parsed_commits):
                parsed_commits.append(p)
                
    bump_type = determine_bump_type(parsed_commits)
    if not bump_type:
        return {
            "should_release": False,
            "reason": f"No releasing conventional commit types found in PR #{pr_number} ('{pr_title}')"
        }
        
    latest_tag = get_latest_git_tag()
    new_tag = compute_next_version(latest_tag, bump_type)
    changelog = generate_changelog(
        parsed_commits,
        pr_number=pr_number,
        pr_author=pr_author,
        pr_url=pr_url
    )
    
    return {
        "should_release": True,
        "bump_type": bump_type,
        "previous_tag": latest_tag or "none",
        "tag_name": new_tag,
        "version": new_tag.lstrip("v"),
        "release_title": f"Wiedźmin: Dziki Zgon {new_tag}",
        "changelog": changelog
    }

def update_title_version(version: str, title_file: Optional[Path] = None) -> bool:
    """
    Updates the first line of texts/title.txt to reflect the new release version.
    Centers the text in a 40-character line according to ANTIC 2 requirements.
    Preserves all subsequent lines.
    """
    if title_file is None:
        title_file = Path("texts/title.txt")
    if isinstance(title_file, str):
        title_file = Path(title_file)
        
    if not title_file.exists():
        return False
        
    with open(title_file, "r", encoding="utf-8") as f:
        lines = [l.rstrip("\r\n") for l in f.readlines() if l.rstrip("\r\n")]
        
    clean_version = version.lstrip("v").strip()
    line1 = f"dziki zgon wersja {clean_version}".center(40)
    
    output_lines = [line1]
    if len(lines) > 1:
        for extra in lines[1:]:
            output_lines.append(extra.ljust(40)[:40])
    else:
        output_lines.append("  https://github.com/grzes71/dziki-zgon  ")
        
    with open(title_file, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines) + "\n")
    return True

def main():
    parser = argparse.ArgumentParser(description="Analyze PR and determine release version")
    parser.add_argument("--event-path", help="Path to GITHUB_EVENT_PATH JSON file")
    parser.add_argument("--output-file", help="Path to save GITHUB_OUTPUT key-value pairs")
    parser.add_argument("--changelog-file", help="Path to save changelog markdown")
    parser.add_argument("--update-title", action="store_true", help="Update texts/title.txt with the computed or specified version")
    parser.add_argument("--version", help="Specific version string for --update-title")
    parser.add_argument("--title-file", default="texts/title.txt", help="Path to title.txt (default: texts/title.txt)")
    args = parser.parse_args()
    
    # Standalone title update mode
    if args.version and args.update_title:
        updated = update_title_version(args.version, Path(args.title_file))
        if updated:
            print(f"Updated {args.title_file} with version {args.version}")
        else:
            print(f"Failed to update {args.title_file}", file=sys.stderr)
        return

    if not args.event_path:
        print("Error: --event-path or (--update-title --version ...) required", file=sys.stderr)
        sys.exit(1)
        
    with open(args.event_path, "r", encoding="utf-8") as f:
        event_data = json.load(f)
        
    # Analyze only the commits brought in by this PR (via its merge commit),
    # not an arbitrary window of the target branch history.
    merge_sha = event_data.get("pull_request", {}).get("merge_commit_sha")
    git_commits = get_pr_commit_messages(merge_sha)

    result = process_github_pr_event(event_data, git_commits)
    print(f"Release Decision: {json.dumps(result, indent=2)}")
    
    # Update title.txt if requested and release is approved
    if args.update_title and result.get("should_release"):
        update_title_version(result["version"], Path(args.title_file))
        print(f"Updated {args.title_file} with version {result['version']}")

    # Write to GITHUB_OUTPUT if specified
    if args.output_file:
        with open(args.output_file, "a", encoding="utf-8") as f:
            f.write(f"should_release={str(result['should_release']).lower()}\n")
            if result["should_release"]:
                f.write(f"tag_name={result['tag_name']}\n")
                f.write(f"version={result['version']}\n")
                f.write(f"release_title={result['release_title']}\n")
                f.write(f"bump_type={result['bump_type']}\n")
                f.write(f"previous_tag={result['previous_tag']}\n")
                
    if args.changelog_file and result.get("should_release"):
        with open(args.changelog_file, "w", encoding="utf-8") as f:
            f.write(result.get("changelog", ""))

if __name__ == "__main__":
    main()
