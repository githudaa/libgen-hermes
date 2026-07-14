#!/usr/bin/env python3
"""Resumeable artifact download"""
import os, time, requests, zipfile

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
os.makedirs(output_dir, exist_ok=True)
tmp_path = os.path.join(output_dir, "_big.zip")

url = "https://api.github.com/repos/githudaa/libgen-hermes/actions/artifacts/" + art_id + "/zip"
headers = {"Authorization": auth}

# Remove stale partials
for f in [tmp_path, os.path.join(output_dir, "big_book.zip")]:
    if os.path.exists(f):
        os.remove(f)
        print(f"Removed stale: {f}")

# Retry loop
max_retries = 10
for attempt in range(max_retries):
    try:
        existing = os.path.getsize(tmp_path) if os.path.exists(tmp_path) else 0
        headers["Range"] = "bytes=" + str(existing) + "-"
        
        print(f"Attempt {attempt+1}/{max_retries} (resume from {existing:,} bytes)...")
        r = requests.get(url, headers=headers, stream=True, timeout=(30, 120))
        if r.status_code in (200, 206):
            mode = "ab" if r.status_code == 206 else "wb"
            with open(tmp_path, mode) as f:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
            sz = os.path.getsize(tmp_path)
            print(f"  -> {sz:,} bytes (HTTP {r.status_code})")
            if r.status_code == 200:
                break
        else:
            print(f"  HTTP {r.status_code}, retrying in 10s...")
            time.sleep(10)
    except Exception as e:
        print(f"  Error: {e}, retrying in 10s...")
        time.sleep(10)

final_size = os.path.getsize(tmp_path)
print(f"\nFinal size: {final_size:,} bytes")

if final_size > 1000:
    try:
        with zipfile.ZipFile(tmp_path) as zf:
            for f in zf.namelist():
                zf.extract(f, output_dir)
                fpath = os.path.join(output_dir, f)
                print(f"  -> {f} ({os.path.getsize(fpath):,} bytes)")
        os.remove(tmp_path)
        print("DONE")
    except zipfile.BadZipFile:
        print("Still corrupt, keeping for resume")
