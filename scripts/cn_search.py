#!/usr/bin/env python3
"""
中文教材一键搜书下载
用法: python3 cn_search.py <中文书名> [格式]

流程: 中文书名 → 英文翻译 → GitHub Actions LibGen搜索 → 等待 → 下载
"""
import os, sys, json, subprocess, time

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cn_translate import translate

# Config
OWNER = "githudaa"
REPO = "libgen-hermes"
API = "https://api.github.com"
OUTPUT_DIR = os.path.expanduser("~/Desktop/libgen_downloads")

# Load token
token = None
with open(os.path.expanduser("~/.zshrc")) as f:
    for raw in f:
        line = raw.strip()
        if "GITHUB_TOKEN" in line and not line.startswith("#"):
            token = line.partition("=")[2].strip().strip('"').strip("'")
            break

if not token:
    print("ERROR: GITHUB_TOKEN not set")
    sys.exit(1)

auth = "Bearer " + token


def gh(path, timeout=15):
    r = subprocess.run([
        "curl", "-s",
        "-H", "Accept: application/vnd.github+json",
        "-H", "Authorization: " + auth,
        "-H", "X-GitHub-Api-Version: 2022-11-28",
        API + path
    ], capture_output=True, text=True, timeout=timeout)
    return json.loads(r.stdout) if r.stdout.strip() else {}


def trigger(query, fmt="pdf"):
    payload = json.dumps({
        "ref": "main",
        "inputs": {"query": query, "format": fmt, "download_index": "1", "result_limit": "10"}
    })
    r = subprocess.run([
        "curl", "-s", "-w", "\n%{http_code}", "-X", "POST",
        "-H", "Accept: application/vnd.github+json",
        "-H", "Authorization: " + auth,
        f"{API}/repos/{OWNER}/{REPO}/actions/workflows/libgen.yml/dispatches",
        "-d", payload
    ], capture_output=True, text=True, timeout=15)
    return "204" in r.stdout


def wait_for_run(run_id, timeout=600):
    """Wait for a specific run to complete"""
    start = time.time()
    while time.time() - start < timeout:
        run = gh(f"/repos/{OWNER}/{REPO}/actions/runs/{run_id}")
        status = run.get("status", "?")
        conclusion = run.get("conclusion")
        if status == "completed":
            return conclusion == "success"
        time.sleep(10)
    return False


def get_latest_run_id():
    """Get the latest workflow_dispatch run ID"""
    runs = gh(f"/repos/{OWNER}/{REPO}/actions/runs?event=workflow_dispatch&per_page=3")
    for run in runs.get("workflow_runs", []):
        return run["id"]
    return None


def download_artifact(run_id):
    """Download book artifact from completed run"""
    arts = gh(f"/repos/{OWNER}/{REPO}/actions/runs/{run_id}/artifacts")
    for art in arts.get("artifacts", []):
        if art["name"].startswith("books-") and art.get("size_in_bytes", 0) > 1000:
            tmp = f"/tmp/libgen_{run_id}.zip"
            subprocess.run([
                "curl", "-s", "-L", "-o", tmp, "--max-time", "600",
                "-H", "Authorization: " + auth,
                f"{API}/repos/{OWNER}/{REPO}/actions/artifacts/{art['id']}/zip"
            ], timeout=620)
            if os.path.exists(tmp) and os.path.getsize(tmp) > 100:
                import zipfile
                os.makedirs(OUTPUT_DIR, exist_ok=True)
                with zipfile.ZipFile(tmp) as zf:
                    for f in zf.namelist():
                        zf.extract(f, OUTPUT_DIR)
                        fpath = os.path.join(OUTPUT_DIR, f)
                        print(f"  ✅ {f} ({os.path.getsize(fpath):,} bytes)")
                os.remove(tmp)
                return True
    return False


def search_cn(cn_title, author="", fmt="pdf"):
    """一站式: 中文书名 → 搜索 → 下载"""
    print(f"\n{'='*60}")
    print(f"📖 {cn_title}")
    print(f"{'='*60}")

    # Translate
    queries = translate(cn_title, author)
    print(f"🔤 翻译: {queries[0] if queries else cn_title}")

    # Trigger each query until one succeeds
    for i, q in enumerate(queries[:3]):  # try top 3
        print(f"\n  🔍 [{i+1}/{min(3,len(queries))}] {q}")
        if not trigger(q, fmt):
            print(f"  ❌ 触发失败")
            continue

        # Get run ID
        time.sleep(2)
        run_id = get_latest_run_id()
        if not run_id:
            print(f"  ❌ 无法获取 run ID")
            continue

        print(f"  ⏳ 等待执行... (run #{run_id})")
        success = wait_for_run(run_id, timeout=300)

        if success:
            print(f"  📥 下载中...")
            if download_artifact(run_id):
                return True
        else:
            print(f"  ⚠️ 未找到或失败，尝试下一个搜索词")

    print(f"  ❌ 所有搜索词均未找到")
    return False


# ═══ Main ═══
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 cn_search.py <中文书名> [作者]")
        print("示例: python3 cn_search.py '陈阅增普通生物学' '吴相钰'")
        sys.exit(1)

    title = sys.argv[1]
    author = sys.argv[2] if len(sys.argv) > 2 else ""
    search_cn(title, author)
