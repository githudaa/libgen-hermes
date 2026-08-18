#!/usr/bin/env python3
"""云端查看LibGen拦截页内容 + 试更多下载路径"""
import subprocess, time

md5 = "2a49ff5a214eecfee4c5df15ce385c96"  # Making Comics

# 1. 看 get.php 返回的 638 字节内容
r = subprocess.run(["curl","-s","-L","--max-time","20",
    f"https://libgen.li/get.php?md5={md5}"], capture_output=True, text=True, timeout=30)
print("=== libgen.li get.php 响应内容 ===")
print(r.stdout[:600])
print("===")
time.sleep(2)

# 2. 带 Referer + UA 模拟真实浏览器
r2 = subprocess.run(["curl","-s","-L","--max-time","20",
    "-H","Referer: https://libgen.li/",
    "-H","User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0",
    f"https://libgen.li/get.php?md5={md5}"], capture_output=True, text=True, timeout=30)
print("=== 带Referer/UA ===")
print(f"长度: {len(r2.stdout)}")
print(r2.stdout[:300])
time.sleep(2)

# 3. libgen.la / libgen.vg 的 ads.php 和 get.php
for base in ["https://libgen.la", "https://libgen.vg"]:
    for path in [f"/ads.php?md5={md5}", f"/get.php?md5={md5}"]:
        r3 = subprocess.run(["curl","-s","-o","/dev/null","-w","%{http_code} %{size_download}",
            "-L","--max-time","20", base+path], capture_output=True, text=True, timeout=30)
        print(f"{base}{path}: {r3.stdout}")
        time.sleep(1)

# 4. libgen.li 的搜索页确认结果存在
r4 = subprocess.run(["curl","-s","-L","--max-time","20",
    f"https://libgen.li/index.php?req={md5}"], capture_output=True, text=True, timeout=30)
print(f"\nlibgen.li 搜索页: {len(r4.stdout)} bytes")
