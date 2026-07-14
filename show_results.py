#!/usr/bin/env python3
"""Fetch results JSON for successful runs"""
import os, json, subprocess, zipfile

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
        "https://api.github.com" + path
    ], capture_output=True, text=True, timeout=15)
    return json.loads(r.stdout) if r.stdout.strip() else {}

# Get results from key successful runs
runs = gh_api("/repos/githudaa/libgen-hermes/actions/runs?per_page=20&status=success")
for run in runs.get("workflow_runs", []):
    rid = run["id"]
    # Get results artifact
    arts = gh_api(f"/repos/githudaa/libgen-hermes/actions/runs/{rid}/artifacts")
    for art in arts.get("artifacts", []):
        if art["name"].startswith("results-") and art.get("size_in_bytes", 0) > 500:
            tmp = f"/tmp/res_{rid}.zip"
            subprocess.run([
                "curl", "-s", "-L", "-o", tmp, "--max-time", "30",
                "-H", "Authorization: " + auth,
                f"https://api.github.com/repos/githudaa/libgen-hermes/actions/artifacts/{art['id']}/zip"
            ], timeout=35)
            if os.path.exists(tmp) and os.path.getsize(tmp) > 50:
                try:
                    with zipfile.ZipFile(tmp) as zf:
                        for f in zf.namelist():
                            data = json.loads(zf.read(f))
                            print(f"\n=== Run #{rid} ===")
                            print(f"Query: {data.get('query','?')}")
                            print(f"Results: {data.get('total_results',0)}, Downloaded: {data.get('downloaded',0)}")
                            for r in data.get("results", [])[:5]:
                                print(f"  [{r['extension']}] {r['title'][:80]}")
                                print(f"       {r.get('size','?')} | {r.get('author','?')[:50]}")
                except:
                    pass
                os.remove(tmp)
