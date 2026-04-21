#!/usr/bin/env python3
"""
update_readme.py
Fetches latest commit across all public repos for ars-devsecops
and updates the dynamic section of README.md
"""

import os
import re
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

USERNAME = "ars-devsecops"
README   = "README.md"
TOKEN    = os.environ.get("GH_PAT", "")

HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "readme-updater"
}

IST = timezone(timedelta(hours=5, minutes=30))


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code} for {url}: {e.reason}")
        return None
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def get_latest_repo_and_commit():
    repos = fetch(
        f"https://api.github.com/users/{USERNAME}/repos"
        f"?sort=pushed&per_page=15&type=public"
    )
    if not repos:
        return None, None, None, None

    # Skip the profile repo itself and forks
    target_repo = None
    for r in repos:
        if r["name"] != USERNAME and not r.get("fork", False):
            target_repo = r
            break

    if not target_repo:
        return None, None, None, None

    repo_name = target_repo["name"]
    print(f"Latest active repo: {repo_name}")

    commits = fetch(
        f"https://api.github.com/repos/{USERNAME}/{repo_name}/commits?per_page=1"
    )
    if not commits or len(commits) == 0:
        return repo_name, "Initial commit", "unknown", "recently"

    commit      = commits[0]
    message     = commit["commit"]["message"].split("\n")[0][:65]
    sha         = commit["sha"][:7]
    raw_date    = commit["commit"]["author"]["date"]

    try:
        dt          = datetime.strptime(raw_date, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        commit_date = dt.astimezone(IST).strftime("%d %b %Y")
    except Exception:
        commit_date = "recently"

    return repo_name, message, sha, commit_date


def main():
    if not TOKEN:
        print("ERROR: GH_PAT environment variable is not set")
        exit(1)

    print("Fetching latest activity...")
    repo_name, commit_msg, commit_sha, commit_date = get_latest_repo_and_commit()

    # Refreshed time in IST
    now_ist   = datetime.now(IST)
    refreshed = now_ist.strftime("%d %b %Y · %I:%M %p IST")

    print(f"Refreshed:     {refreshed}")
    print(f"Repo:          {repo_name}")
    print(f"Commit:        {commit_sha} — {commit_msg}")
    print(f"Commit date:   {commit_date}")

    if repo_name:
        new_block = (
            "<!-- DYNAMIC_STATS_START -->\n"
            f"> ⏱️ **Last refreshed:** {refreshed}\n"
            ">\n"
            f"> 🔀 **Latest commit:** `{commit_sha}` — {commit_msg}\n"
            f"> 📁 **Repo:** [{repo_name}](https://github.com/{USERNAME}/{repo_name}) · {commit_date}\n"
            "<!-- DYNAMIC_STATS_END -->"
        )
    else:
        new_block = (
            "<!-- DYNAMIC_STATS_START -->\n"
            f"> ⏱️ **Last refreshed:** {refreshed}\n"
            "<!-- DYNAMIC_STATS_END -->"
        )

    with open(README, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"<!-- DYNAMIC_STATS_START -->.*?<!-- DYNAMIC_STATS_END -->"
    if not re.search(pattern, content, flags=re.DOTALL):
        print("ERROR: Dynamic markers not found in README.md")
        print("Make sure README.md contains:")
        print("<!-- DYNAMIC_STATS_START -->")
        print("<!-- DYNAMIC_STATS_END -->")
        exit(1)

    updated = re.sub(pattern, new_block, content, flags=re.DOTALL)

    with open(README, "w", encoding="utf-8") as f:
        f.write(updated)

    print("README.md updated successfully")


if __name__ == "__main__":
    main()
