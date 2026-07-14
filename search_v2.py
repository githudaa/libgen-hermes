#!/usr/bin/env python3
"""Search LibGen with smarter English queries for the 6 missing books"""
import os, json, subprocess, time

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
        "curl", "-s", "-w", "\n%{http_code}", "-X", "POST",
        "-H", "Accept: application/vnd.github+json",
        "-H", "Authorization: " + auth,
        "-H", "X-GitHub-Api-Version: 2022-11-28",
        "https://api.github.com/repos/githudaa/libgen-hermes/actions/workflows/libgen.yml/dispatches",
        "-d", payload
    ], capture_output=True, text=True, timeout=15)
    return "204" in r.stdout

# Smarter queries - broader terms for international textbooks
# For Chinese-only textbooks, try the general English equivalent
searches = [
    # Campbell Biology - should definitely exist, try broader
    ("Campbell生物学11版", "Campbell Biology"),
    ("Campbell生物学11版", "Campbell Biology Urry"),
    # Lehninger - should exist  
    ("Lehninger生物化学8版", "Lehninger Principles Biochemistry"),
    ("Lehninger生物化学8版", "Lehninger Biochemistry"),
    # 陈阅增普通生物学 - try just "General Biology" 
    ("陈阅增普通生物学", "General Biology 4th edition"),
    # 基础生命科学 - try life science
    ("基础生命科学", "Life Science fundamentals"),
    # 生物学第6版 - try broader
    ("生物学第6版", "Biology textbook 6th edition"),
    # 生物化学第4版 - try broader biochemistry
    ("生物化学第4版", "Biochemistry 4th edition textbook"),
    # 生物化学原理第3版
    ("生物化学原理第3版", "Principles of Biochemistry textbook"),
]

print("=" * 60)
for cn, en in searches:
    print(f"📖 {cn[:20]}")
    print(f"   🔍 {en}")
    ok = trigger(en)
    print(f"   {'✅' if ok else '❌'}")
    time.sleep(2)

print("\n全部触发 ✓")
