#!/usr/bin/env python3
"""archive.org 下载器 - 云端运行，绕过墙"""
import json, os, sys, time, urllib.request, urllib.parse

IDENTIFIER = os.environ.get("IA_IDENTIFIER", "")
FILENAME = os.environ.get("IA_FILENAME", "")
DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "./downloads")
RESULTS_FILE = os.environ.get("RESULTS_FILE", "./results.json")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def fetch(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; libgen-hermes/1.0)"})
    return urllib.request.urlopen(req, timeout=timeout)

def get_metadata(identifier):
    """获取 archive.org 条目的文件列表"""
    url = f"https://archive.org/metadata/{identifier}"
    with fetch(url) as r:
        data = json.loads(r.read().decode())
    return data

def download_file(identifier, filename, dest):
    """下载单文件（直连 archive.org/download/）"""
    url = f"https://archive.org/download/{identifier}/{urllib.parse.quote(filename)}"
    tmp = dest + ".part"
    with fetch(url) as r, open(tmp, "wb") as f:
        while True:
            chunk = r.read(1024 * 256)
            if not chunk:
                break
            f.write(chunk)
    os.rename(tmp, dest)
    return os.path.getsize(dest)

def main():
    if not IDENTIFIER:
        print("ERROR: IA_IDENTIFIER 为空")
        sys.exit(1)
    print(f"identifier={IDENTIFIER}, filename={FILENAME or '(自动取最大文件)'}")
    meta = get_metadata(IDENTIFIER)
    files = [f for f in meta.get("files", []) if f.get("name") and f["name"].endswith((".pdf", ".epub", ".mobi", ".djvu", ".txt"))]
    print(f"文件列表: {[f['name'] for f in files]}")
    if not files:
        print("ERROR: 无可下载文件")
        sys.exit(1)
    if FILENAME:
        target = FILENAME
        if not any(f["name"] == target for f in files):
            print(f"ERROR: 文件名 {target} 不在列表中")
            sys.exit(1)
    else:
        # 自动选最大的 pdf/epub
        def size_key(f):
            return int(f.get("size", 0) or 0)
        target = max(files, key=size_key)["name"]
    safe = target.replace("/", "_")
    dest = os.path.join(DOWNLOAD_DIR, safe)
    print(f"下载: {target} -> {dest}")
    t0 = time.time()
    size = download_file(IDENTIFIER, target, dest)
    print(f"完成: {size} bytes, 耗时 {time.time()-t0:.1f}s")
    with open(RESULTS_FILE, "w") as f:
        json.dump({"identifier": IDENTIFIER, "file": target, "size": size, "path": dest}, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
