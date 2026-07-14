#!/usr/bin/env python3
"""Download specific artifact"""
import os, subprocess, zipfile

token = None
with open(os.path.expanduser("~/.zshrc")) as f:
    for raw in f:
        line = raw.strip()
        if "GITHUB_TOKEN" in line and not line.startswith("#"):
            token = line.partition("=")[2].strip().strip('"').strip("'")
            break

auth = "Bearer " + token
art_id = "8302809015"
output_dir = os.path.expanduser("~/Desktop/libgen_downloads")
tmp = os.path.join(output_dir, "_tmp.zip")
os.makedirs(output_dir, exist_ok=True)

print("Downloading artifact 8302809015...")
r = subprocess.run([
    "curl", "-s", "-L", "-o", tmp, "--max-time", "600",
    "-H", "Authorization: " + auth,
    f"https://api.github.com/repos/githudaa/libgen-hermes/actions/artifacts/{art_id}/zip"
], timeout=620)

sz = os.path.getsize(tmp) if os.path.exists(tmp) else 0
print(f"Downloaded: {sz:,} bytes")

if sz > 100:
    with zipfile.ZipFile(tmp) as zf:
        for f in zf.namelist():
            zf.extract(f, output_dir)
            fpath = os.path.join(output_dir, f)
            fsize = os.path.getsize(fpath)
            print(f"  -> {f} ({fsize:,} bytes)")
    os.remove(tmp)
    print("DONE")
else:
    print("FAILED")
