#!/usr/bin/env python3
"""Fetch result JSONs from completed runs to debug failures"""
import os, json, subprocess, sys

token = None
with open(os.path.expanduser("~/.zshrc")) as f:
    for raw in f:
        line = raw.strip()
        if "GITHUB_TOKEN" in line and not line.startswith("#"):
            token = line.partition("=")[2].strip().strip('"').strip("'")
            break

auth = "Bearer " + token

def gh_api(path):
    r = subprocess.run([
        "curl", "-s",
        "-H", "Accept: application/vnd.github+json",
        "-H", "Authorization: " + auth,
        "-H", "X-GitHub-Api-Version: 2022-11-28",
        "https://api.github.com" + path
    ], capture_output=True, text=True, timeout=30)
    return json.loads(r.stdout) if r.stdout.strip() else {}

def dl_json(art_id, name):
    tmp = f"/tmp/{name}.zip"
    r = subprocess.run([
        "curl", "-s", "-L", "-o", tmp,
        "-H", "Authorization: " + auth,
        f"https://api.github.com/repos/githudaa/libgen-hermes/actions/artifacts/{art_id}/zip"
    ], capture_output=True, text=True, timeout=60)
    if os.path.exists(tmp) and os.path.getsize(tmp) > 50:
        import zipfile
        with zipfile.ZipFile(tmp) as zf:
            for f in zf.namelist():
                data = zf.read(f)
                try:
                    obj = json.loads(data)
                    print(f"  query: {obj.get('query','?')}")
                    print(f"  results: {obj.get('total_results',0)}")
                    if obj.get('error'):
                        print(f"  error: {obj['error']}")
                    for r in obj.get('results', [])[:3]:
                        print(f"    - {r['title'][:60]} ({r['extension']})")
                except:
                    print(f"  raw: {data[:200]}")
        os.remove(tmp)

# Check recent failed runs
runs = gh_api("/repos/githudaa/libgen-hermes/actions/runs?per_page=20")
for run in runs.get("workflow_runs", []):
    s = run.get("status", "?")
    c = run.get("conclusion", "?")
    rid = run["id"]
    t = run.get("display_title", "?")[:50]
    
    if s == "completed" and c == "failure":
        print(f"\n#{rid} FAILED: {t}")
        arts = gh_api(f"/repos/githudaa/libgen-hermes/actions/runs/{rid}/artifacts")
        for art in arts.get("artifacts", []):
            if art["name"].startswith("results-") and art.get("size_in_bytes", 0) > 100:
                dl_json(art["id"], art["name"])
