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
    """下载单文件（直连 archive.org/download/），带重试"""
    url = f"https://archive.org/download/{identifier}/{urllib.parse.quote(filename)}"
    tmp = dest + ".part"
    max_attempts = 5
    for attempt in range(1, max_attempts + 1):
        try:
            with fetch(url) as r, open(tmp, "wb") as f:
                while True:
                    chunk = r.read(1024 * 256)
                    if not chunk:
                        break
                    f.write(chunk)
            os.rename(tmp, dest)
            return os.path.getsize(dest)
        except Exception as e:
            print(f"  第{attempt}次失败: {str(e)[:100]}")
            if attempt < max_attempts:
                time.sleep(5 * attempt)
    raise RuntimeError(f"下载失败（重试{max_attempts}次）: {filename}")

def main():
    if not IDENTIFIER:
        print("ERROR: IA_IDENTIFIER 为空")
        sys.exit(1)
    print(f"identifier={IDENTIFIER}, filename={FILENAME or '(自动取最大文件)'}")
    meta = get_metadata(IDENTIFIER)
    files = [f for f in meta.get("files", []) if f.get("name") and f["name"].endswith((".pdf", ".epub", ".mobi", ".djvu", ".txt"))]
    print(f"文件列表({len(files)}):")
    for f in files:
        print(f"  - {f['name']} | {int(f.get('size', 0) or 0)//1024}KB | {f.get('format','')}")
    if os.environ.get("IA_LIST_ONLY", "0") == "1":
        print("LIST_ONLY=1，跳过下载")
        sys.exit(0)
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
