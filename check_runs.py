#!/usr/bin/env python3
import os, json, subprocess, sys

# Load token
token = None
with open(os.path.expanduser("~/.zshrc")) as f:
    for raw in f:
        line = raw.strip()
        if "GITHUB_TOKEN" in line and not line.startswith("#"):
            token = line.partition("=")[2].strip().strip('"').strip("'")
            break

if not token:
    print("ERROR")
    sys.exit(1)

print(f"OK {len(token)} chars")

def gh(path):
    auth = "Bearer " + token
    r = subprocess.run([
        "curl", "-s",
        "-H", "Accept: application/vnd.github+json",
        "-H", "Authorization: " + auth,
        "-H", "X-GitHub-Api-Version: 2022-11-28",
        "https://api.github.com" + path
    ], capture_output=True, text=True, timeout=30)
    return json.loads(r.stdout) if r.stdout.strip() else {}

runs = gh("/repos/githudaa/libgen-hermes/actions/runs?per_page=15")
for run in runs.get("workflow_runs", []):
    s, c = run.get("status","?"), run.get("conclusion","?")
    rid = run.get("id","?")
    t = run.get("display_title","?")[:50]
    print(f"#{rid} [{s}/{c}] {t}")
