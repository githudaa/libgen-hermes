#!/usr/bin/env python3
"""Download specific artifact with resume"""
import os, time, requests, zipfile, sys

token = None
with open(os.path.expanduser("~/.zshrc")) as f:
    for raw in f:
        line = raw.strip()
        if "GITHUB_TOKEN" in line and not line.startswith("#"):
            token = line.partition("=")[2].strip().strip('"').strip("'")
            break

auth = "Bearer " + token
art_id = sys.argv[1] if len(sys.argv) > 1 else "8303400421"
tag = sys.argv[2] if len(sys.argv) > 2 else "book"

output_dir = os.path.expanduser("~/Desktop/libgen_downloads")
os.makedirs(output_dir, exist_ok=True)
tmp_path = os.path.join(output_dir, "_" + tag + ".zip")

url = "https://api.github.com/repos/githudaa/libgen-hermes/actions/artifacts/" + art_id + "/zip"
headers = {"Authorization": auth}

# Remove if exists (start fresh to avoid 416)
if os.path.exists(tmp_path):
    os.remove(tmp_path)

for attempt in range(5):
    try:
        existing = os.path.getsize(tmp_path) if os.path.exists(tmp_path) else 0
        if existing > 0:
            headers["Range"] = "bytes=" + str(existing) + "-"
        
        print(f"Attempt {attempt+1} (from {existing:,} bytes)...")
        r = requests.get(url, headers=headers, stream=True, timeout=(30, 300))
        
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
        elif r.status_code == 416:
            print(f"  Already complete ({existing:,} bytes)")
            break
        else:
            print(f"  HTTP {r.status_code}, retry in 10s")
            time.sleep(10)
    except Exception as e:
        print(f"  Error: {e}, retry in 10s")
        time.sleep(10)

final_size = os.path.getsize(tmp_path) if os.path.exists(tmp_path) else 0
print(f"Final: {final_size:,} bytes")

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
        print("CORRUPT")
