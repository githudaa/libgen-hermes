#!/usr/bin/env python3
"""Download book artifacts from GitHub Actions (v2 - skip downloaded, longer timeout)"""
import os, json, subprocess, sys, zipfile

token = None
with open(os.path.expanduser("~/.zshrc")) as f:
    for raw in f:
        line = raw.strip()
        if "GITHUB_TOKEN" in line and not line.startswith("#"):
            token = line.partition("=")[2].strip().strip('"').strip("'")
            break

auth = "Bearer " + token
output_dir = os.path.expanduser("~/Desktop/libgen_downloads")
os.makedirs(output_dir, exist_ok=True)
downloaded_ids = set()

# Scan already downloaded
for f in os.listdir(output_dir):
    if f.endswith(".id"):
        with open(os.path.join(output_dir, f)) as ff:
            downloaded_ids.add(ff.read().strip())

def gh_api(path):
    r = subprocess.run([
        "curl", "-s",
        "-H", "Accept: application/vnd.github+json",
        "-H", "Authorization: " + auth,
        "-H", "X-GitHub-Api-Version: 2022-11-28",
        "https://api.github.com" + path
    ], capture_output=True, text=True, timeout=30)
    return json.loads(r.stdout) if r.stdout.strip() else {}

def dl_artifact(art_id, name):
    tmp = f"/tmp/{name}.zip"
    print(f"     downloading ({name})...", flush=True)
    r = subprocess.run([
        "curl", "-s", "-L", "-o", tmp,
        "-H", "Authorization: " + auth,
        f"https://api.github.com/repos/githudaa/libgen-hermes/actions/artifacts/{art_id}/zip"
    ], capture_output=True, text=True, timeout=300)
    
    if os.path.exists(tmp) and os.path.getsize(tmp) > 100:
        try:
            with zipfile.ZipFile(tmp) as zf:
                for f in zf.namelist():
                    zf.extract(f, output_dir)
                    fpath = os.path.join(output_dir, f)
                    size = os.path.getsize(fpath)
                    print(f"     saved: {f} ({size:,} bytes)")
            # Mark as downloaded
            with open(os.path.join(output_dir, f"{art_id}.id"), "w") as ff:
                ff.write(str(art_id))
            os.remove(tmp)
            return True
        except zipfile.BadZipFile:
            print(f"     BAD ZIP, raw size={os.path.getsize(tmp)}")
            os.remove(tmp)
    else:
        sz = os.path.getsize(tmp) if os.path.exists(tmp) else 0
        print(f"     FAILED: zip size={sz}, stderr={r.stderr[:100]}")
        if os.path.exists(tmp):
            os.remove(tmp)
    return False

# List runs
runs = gh_api("/repos/githudaa/libgen-hermes/actions/runs?per_page=15")
for run in runs.get("workflow_runs", []):
    s = run.get("status", "?")
    c = run.get("conclusion", "?")
    rid = run["id"]
    t = run.get("display_title", "?")[:50]
    print(f"#{rid} [{s}/{c}] {t}")

    if s == "completed":
        arts = gh_api(f"/repos/githudaa/libgen-hermes/actions/runs/{rid}/artifacts")
        for art in arts.get("artifacts", []):
            aname = art["name"]
            aid = art["id"]
            size = art.get("size_in_bytes", 0)
            print(f"  -> {aname} ({size:,} bytes)")
            
            if aname.startswith("books-") and size > 100:
                if str(aid) in downloaded_ids:
                    print(f"     (already downloaded, skip)")
                else:
                    dl_artifact(aid, aname)

print(f"\nDone: {output_dir}")
print(f"Files: {len([f for f in os.listdir(output_dir) if not f.endswith('.id')])}")
