#!/usr/bin/env python3
"""Trigger LibGen search via GitHub Actions workflow_dispatch"""
import os, sys, re

# Read token from ~/.zshrc (no inline token)
token = None
rc_path = os.path.expanduser("~/.zshrc")
with open(rc_path) as f:
    for line in f:
        m = re.match(r'export GITHUB_TOKEN=(.+)', line)
        if m:
            token = m.group(1).strip().strip('"').strip("'")
            break

if not token:
    print("ERROR: GITHUB_TOKEN not found")
    print("Run: grep GITHUB_TOKEN ~/.zshrc")
    sys.exit(1)

query = sys.argv[1] if len(sys.argv) > 1 else "Campbell Biology"
fmt = sys.argv[2] if len(sys.argv) > 2 else "pdf"

import json, subprocess
payload = json.dumps({
    "ref": "main",
    "inputs": {
        "query": query,
        "format": fmt,
        "download_index": "1",
        "result_limit": "10"
    }
})

url = "https://api.github.com/repos/githudaa/libgen-hermes/actions/workflows/libgen.yml/dispatches"
proc = subprocess.run([
    "curl", "-s", "-w", "\nHTTP:%{http_code}", "-X", "POST",
    "-H", "Accept: application/vnd.github+json",
    "-H", f"Authorization: Bearer {token}",
    "-H", "X-GitHub-Api-Version: 2022-11-28",
    url, "-d", payload
], capture_output=True, text=True, timeout=30)

print(proc.stdout)
print(proc.stderr[:200] if proc.stderr else "")
