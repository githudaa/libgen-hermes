#!/usr/bin/env python3
"""
Hermes 端辅助脚本 - 通过 GitHub API 触发搜书 & 轮询结果 & 下载 artifact

使用流程:
  1. hermes 调用 trigger_search() 发起搜索
  2. hermes 调用 wait_for_completion() 等待完成
  3. hermes 调用 download_artifact() 下载书籍文件

前置条件:
  - GitHub Personal Access Token (需要 repo 权限)
  - 已创建 GitHub 仓库并上传了 libgen-hermes 项目
"""

import json
import time
import requests
import zipfile
import io
import os
import sys
from typing import Optional

# ============================================================
# 配置 - 从环境变量读取或直接修改
# ============================================================
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_OWNER = os.environ.get("GITHUB_OWNER", "")       # 你的 GitHub 用户名
GITHUB_REPO = os.environ.get("GITHUB_REPO", "libgen-hermes")  # 仓库名
API_BASE = "https://api.github.com"


def get_headers():
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


# ============================================================
# 1. 触发搜索 (repository_dispatch)
# ============================================================
def trigger_search(query: str, fmt: str = "", download_index: int = 1, result_limit: int = 10) -> dict:
    """
    触发 GitHub Actions 搜索书籍

    参数:
        query: 搜索关键词
        fmt: 文件格式 (pdf/epub/mobi)，留空不过滤
        download_index: 下载第几个结果 (1-based)，0=全部
        result_limit: 搜索结果数量

    返回:
        dict: GitHub API 响应
    """
    url = f"{API_BASE}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/dispatches"
    payload = {
        "event_type": "search_book",
        "client_payload": {
            "query": query,
            "format": fmt,
            "download_index": str(download_index),
            "result_limit": str(result_limit),
        },
    }
    resp = requests.post(url, headers=get_headers(), json=payload)
    if resp.status_code == 204:
        print(f"[OK] 已触发搜索: {query}")
        print(f"     格式: {fmt or '不限'}")
        print(f"     下载第 {download_index} 个结果" if download_index > 0 else "     下载全部结果")
        return {"success": True}
    else:
        print(f"[ERROR] 触发失败: {resp.status_code} {resp.text}")
        return {"success": False, "error": resp.text}


# ============================================================
# 2. 获取最近的 workflow run
# ============================================================
def get_latest_run(event_type: str = "repository_dispatch") -> Optional[dict]:
    """获取最近的 workflow run"""
    url = f"{API_BASE}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/runs"
    params = {"event": event_type, "per_page": 1}
    resp = requests.get(url, headers=get_headers(), params=params)
    if resp.status_code == 200:
        runs = resp.json().get("workflow_runs", [])
        if runs:
            return runs[0]
    return None


def get_run_by_id(run_id: int) -> Optional[dict]:
    """通过 run_id 获取 run 状态"""
    url = f"{API_BASE}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/runs/{run_id}"
    resp = requests.get(url, headers=get_headers())
    if resp.status_code == 200:
        return resp.json()
    return None


# ============================================================
# 3. 等待 workflow 完成
# ============================================================
def wait_for_completion(timeout: int = 600, poll_interval: int = 10) -> Optional[dict]:
    """
    轮询等待最近的 workflow run 完成

    参数:
        timeout: 最大等待时间 (秒)
        poll_interval: 轮询间隔 (秒)

    返回:
        dict: 完成的 run 信息，或 None (超时)
    """
    print(f"[INFO] 等待 workflow 完成 (超时: {timeout}s)...")

    # 先获取最新的 run
    run = get_latest_run()
    if not run:
        print("[ERROR] 未找到 workflow run")
        return None

    run_id = run["id"]
    print(f"[INFO] 监控 run #{run_id} ({run['name']})")

    start = time.time()
    while time.time() - start < timeout:
        run = get_run_by_id(run_id)
        if not run:
            time.sleep(poll_interval)
            continue

        status = run["status"]      # queued / in_progress / completed
        conclusion = run.get("conclusion")  # success / failure / null (still running)

        elapsed = int(time.time() - start)
        print(f"  [{elapsed}s] 状态: {status} / 结论: {conclusion or '运行中...'}")

        if status == "completed":
            if conclusion == "success":
                print(f"[OK] Workflow 成功完成!")
            else:
                print(f"[WARN] Workflow 完成但结论为: {conclusion}")
            return run

        time.sleep(poll_interval)

    print(f"[TIMEOUT] 等待超时 ({timeout}s)")
    return None


# ============================================================
# 4. 列出 artifact
# ============================================================
def list_artifacts(run_id: int) -> list:
    """列出某个 run 的所有 artifact"""
    url = f"{API_BASE}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/runs/{run_id}/artifacts"
    resp = requests.get(url, headers=get_headers())
    if resp.status_code == 200:
        return resp.json().get("artifacts", [])
    print(f"[ERROR] 获取 artifact 列表失败: {resp.status_code}")
    return []


# ============================================================
# 5. 下载 artifact
# ============================================================
def download_artifact(artifact_id: int, output_dir: str = "./downloads") -> bool:
    """
    下载 artifact (ZIP 格式) 并解压

    参数:
        artifact_id: artifact ID
        output_dir: 解压目标目录

    返回:
        bool: 是否成功
    """
    url = f"{API_BASE}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/artifacts/{artifact_id}/zip"
    resp = requests.get(url, headers=get_headers(), stream=True)

    if resp.status_code != 200:
        print(f"[ERROR] 下载 artifact 失败: {resp.status_code} {resp.text}")
        return False

    os.makedirs(output_dir, exist_ok=True)

    # artifact 是 ZIP 格式，直接在内存中解压
    zip_data = io.BytesIO(resp.content)
    with zipfile.ZipFile(zip_data) as zf:
        zf.extractall(output_dir)
        files = zf.namelist()

    print(f"[OK] 已下载 {len(files)} 个文件到 {output_dir}/:")
    for f in files:
        filepath = os.path.join(output_dir, f)
        size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
        print(f"  - {f} ({size:,} bytes)")

    return True


# ============================================================
# 6. 获取搜索结果 JSON
# ============================================================
def fetch_results_json(run_id: int) -> Optional[dict]:
    """从 artifact 中获取搜索结果 JSON"""
    artifacts = list_artifacts(run_id)
    for art in artifacts:
        if art["name"].startswith("results-"):
            # 下载到临时目录
            tmp_dir = "/tmp/libgen_results"
            if download_artifact(art["id"], tmp_dir):
                json_path = os.path.join(tmp_dir, "results.json")
                if os.path.exists(json_path):
                    with open(json_path, "r", encoding="utf-8") as f:
                        return json.load(f)
    return None


# ============================================================
# 完整流程: 搜索 -> 等待 -> 下载
# ============================================================
def search_and_download(query: str, fmt: str = "", download_index: int = 1,
                        result_limit: int = 10, output_dir: str = "./downloads") -> dict:
    """
    一站式: 触发搜索 -> 等待完成 -> 下载书籍文件

    返回:
        dict: 包含搜索结果和下载状态
    """
    # Step 1: 触发
    result = trigger_search(query, fmt, download_index, result_limit)
    if not result.get("success"):
        return result

    # 等2秒让 GitHub 创建 run
    time.sleep(3)

    # Step 2: 等待完成
    run = wait_for_completion(timeout=600, poll_interval=10)
    if not run:
        return {"success": False, "error": "等待超时"}

    run_id = run["id"]

    # Step 3: 获取搜索结果
    results_json = fetch_results_json(run_id)
    if results_json:
        print(f"\n[RESULTS] 搜索到 {results_json.get('total_results', 0)} 条结果")
        for i, book in enumerate(results_json.get("results", [])[:5]):
            print(f"  [{i+1}] {book.get('title', '?')} ({book.get('extension', '?')}, {book.get('size', '?')})")

    # Step 4: 下载书籍文件 artifact
    artifacts = list_artifacts(run_id)
    for art in artifacts:
        if art["name"].startswith("books-"):
            download_artifact(art["id"], output_dir)
            break

    return {
        "success": True,
        "run_id": run_id,
        "results": results_json,
        "output_dir": output_dir,
    }


# ============================================================
# CLI 入口
# ============================================================
if __name__ == "__main__":
    if not GITHUB_TOKEN or not GITHUB_OWNER:
        print("错误: 请设置环境变量 GITHUB_TOKEN 和 GITHUB_OWNER")
        print("  export GITHUB_TOKEN=ghp_xxxxx")
        print("  export GITHUB_OWNER=your_username")
        sys.exit(1)

    if len(sys.argv) < 2:
        print(f"用法: python {sys.argv[0]} <搜索关键词> [格式] [下载索引]")
        print(f"示例: python {sys.argv[0]} '机器学习 周志华' pdf 1")
        sys.exit(1)

    query = sys.argv[1]
    fmt = sys.argv[2] if len(sys.argv) > 2 else ""
    idx = int(sys.argv[3]) if len(sys.argv) > 3 else 1

    result = search_and_download(query, fmt, idx)
    print(f"\n{'='*50}")
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
