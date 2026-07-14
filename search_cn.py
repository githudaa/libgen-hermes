#!/usr/bin/env python3
"""
中文教材 → 英文译名 → LibGen搜索
将中文教材名映射为英文搜索词，触发GitHub Actions搜索下载
"""
import os, re, json, subprocess, sys

token = None
with open(os.path.expanduser("~/.zshrc")) as f:
    for raw in f:
        line = raw.strip()
        if "GITHUB_TOKEN" in line and not line.startswith("#"):
            token = line.partition("=")[2].strip().strip('"').strip("'")
            break

auth = "Bearer " + token

def trigger(query, fmt="pdf"):
    payload = json.dumps({
        "ref": "main",
        "inputs": {"query": query, "format": fmt, "download_index": "1", "result_limit": "10"}
    })
    r = subprocess.run([
        "curl", "-s", "-w", "\nHTTP:%{http_code}", "-X", "POST",
        "-H", "Accept: application/vnd.github+json",
        "-H", "Authorization: " + auth,
        "-H", "X-GitHub-Api-Version: 2022-11-28",
        "https://api.github.com/repos/githudaa/libgen-hermes/actions/workflows/libgen.yml/dispatches",
        "-d", payload
    ], capture_output=True, text=True, timeout=30)
    code = r.stdout.strip().split("\n")[-1].replace("HTTP:", "")
    return code == "204"

# Chinese → English textbook mapping
MAP = {
    "陈阅增普通生物学（第4版）": [
        "General Biology Chen Yuezeng",
        "Chen Yue Zeng General Biology 4th",
    ],
    "基础生命科学（第2版）": [
        "Fundamentals of Life Science Wu Qingyu",
        "Basic Life Science 2nd edition",
    ],
    "Campbell生物学（第11版）": [
        "Campbell Biology 11th edition Urry",
        "Campbell Biology 11e",
    ],
    "生物学（第6版）": [
        "Biology 6th edition Wang Bin Zuo Mingxue",
    ],
    "生物化学（第4版，上下册）": [
        "Biochemistry Wang Jingyan 4th edition",
        "Biochemistry Zhu Shengeng Xu Changfa",
    ],
    "生物化学原理（第3版）": [
        "Principles of Biochemistry Yang Rongwu 3rd",
    ],
    "Lehninger生物化学原理（第8版）": [
        "Lehninger Principles of Biochemistry 8th edition Nelson Cox",
        "Lehninger Principles of Biochemistry 8e",
    ],
}

# Books from the test spreadsheet
print("=" * 60)
print("中文教材 → 英文搜索 → LibGen")
print("=" * 60)

import time
for cn_name, en_queries in MAP.items():
    print(f"\n📖 {cn_name}")
    for eq in en_queries:
        print(f"   🔍 {eq}")
        ok = trigger(eq)
        if ok:
            print(f"   ✅ 已触发")
        else:
            print(f"   ❌ 失败")
        time.sleep(2)

print("\n" + "=" * 60)
print("全部触发完成，等待 GitHub Actions 执行（约2-4分钟）")
