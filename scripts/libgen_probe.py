#!/usr/bin/env python3
"""云端测试 LibGen 各镜像/下载路径可达性，绕过反爬"""
import json, os, subprocess, time

results = {}

def curl_test(url, timeout=25):
    r = subprocess.run(["curl","-s","-o","/dev/null","-w","%{http_code} %{size_download}",
        "-L","--max-time",str(timeout), url], capture_output=True, text=True, timeout=30)
    return r.stdout.strip()

# 1. LibGen 各镜像首页
mirrors = ["https://libgen.li", "https://libgen.is", "https://libgen.rs",
           "https://libgen.gs", "https://libgen.st", "https://libgen.vg",
           "https://libgen.la", "https://libgen.gd", "https://libgen.ee"]
for m in mirrors:
    r = curl_test(m + "/")
    results[m] = r
    print(f"{m}: {r}", flush=True)
    time.sleep(1)

# 2. 已知 md5 的下载路径测试（Making Comics md5=2a49ff5a214eecfee4c5df15ce385c96）
md5 = "2a49ff5a214eecfee4c5df15ce385c96"
paths = [
    ("libgen.li get.php", f"https://libgen.li/get.php?md5={md5}"),
    ("libgen.li get.php+key", "https://libgen.li/get.php?md5=2a49ff5a214eecfee4c5df15ce385c96&key=2a49ff5a214eecfee4c5df15ce385c96"),
    ("libgen.is ads.php", f"https://libgen.is/ads.php?md5={md5}"),
    ("libgen.rs ads.php", f"https://libgen.rs/ads.php?md5={md5}"),
    ("libgen.st ads.php", f"https://libgen.st/ads.php?md5={md5}"),
    ("download.libgen.is", f"https://download.libgen.is/{md5}"),
    ("cdn1.libgen.li", f"https://cdn1.libgen.li/get.php?md5={md5}"),
    ("cdn2.libgen.li", f"https://cdn2.libgen.li/get.php?md5={md5}"),
]
print("\n=== 下载路径测试 (Making Comics md5) ===")
for name, u in paths:
    r = curl_test(u, timeout=20)
    print(f"{name}: {r}", flush=True)
    time.sleep(1)

with open("/tmp/libgen_probe.json", "w") as f:
    json.dump(results, f)
