#!/usr/bin/env python3
"""
LibGen 搜索 & 下载脚本
- 自动尝试多个 LibGen 镜像
- 解析搜索结果并提取下载链接
- 下载书籍文件到本地
- 输出结构化 JSON 结果供 hermes 解析
"""

import json
import os
import re
import sys
import time
import hashlib
import requests
from urllib.parse import urljoin, quote_plus, urlparse
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict
from typing import Optional

# ============================================================
# 镜像配置 - 按优先级排列，脚本会依次尝试
# ============================================================
SEARCH_MIRRORS = [
    "https://libgen.is",
    "https://libgen.rs",
    "https://libgen.li",
    "https://libgen.st",
    "https://libgen.bz",
]

DOWNLOAD_MIRRORS = [
    "https://library.lol",
    "https://libgen.lc",
    "https://libgen.li",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
}

TIMEOUT = 30
DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "./downloads")
RESULTS_FILE = os.environ.get("RESULTS_FILE", "./results.json")


# ============================================================
# 数据结构
# ============================================================
@dataclass
class BookResult:
    title: str
    author: str
    publisher: str
    year: str
    language: str
    pages: str
    size: str
    extension: str
    md5: str
    mirror: str  # 搜索来源镜像
    download_url: Optional[str] = None
    download_status: Optional[str] = None  # "success" / "failed" / "skipped"
    download_path: Optional[str] = None
    error: Optional[str] = None


# ============================================================
# 工具函数
# ============================================================
def try_request(url, method="GET", **kwargs):
    """带重试的 HTTP 请求"""
    kwargs.setdefault("headers", HEADERS)
    kwargs.setdefault("timeout", TIMEOUT)
    kwargs.setdefault("allow_redirects", True)
    for attempt in range(3):
        try:
            resp = requests.request(method, url, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            print(f"  [retry {attempt+1}/3] {url} -> {e}")
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    return None


def find_working_mirror(mirrors, path="/"):
    """依次测试镜像列表，返回第一个可用的"""
    for mirror in mirrors:
        test_url = urljoin(mirror, path)
        resp = try_request(test_url)
        if resp and resp.status_code < 500:
            print(f"[mirror] 使用镜像: {mirror}")
            return mirror
    return None


# ============================================================
# 搜索逻辑 - 支持两种搜索端点
# ============================================================
def search_libgen_is(query, mirror, limit=10):
    """
    搜索 libgen.is / libgen.rs 风格的镜像
    URL: /search.php?req={query}&res={limit}
    """
    search_url = urljoin(mirror, f"/search.php?req={quote_plus(query)}&res={limit}&view=simple")
    print(f"  [search] {search_url}")
    resp = try_request(search_url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    # 结果在 <table> 中，每行是一本 书
    table = soup.find("table", {"class": "c"})
    if not table:
        return results

    rows = table.find_all("tr")
    for row in rows[1:]:  # 跳过表头
        cols = row.find_all("td")
        if len(cols) < 10:
            continue
        try:
            book = BookResult(
                title=cols[2].get_text(strip=True),
                author=cols[1].get_text(strip=True),
                publisher=cols[3].get_text(strip=True),
                year=cols[4].get_text(strip=True),
                language=cols[6].get_text(strip=True),
                pages=cols[5].get_text(strip=True),
                size=cols[7].get_text(strip=True),
                extension=cols[8].get_text(strip=True),
                md5="",
                mirror=mirror,
            )
            # 提取 MD5 - 通常在详情页链接中
            detail_link = cols[2].find("a")
            if detail_link and detail_link.get("href"):
                href = detail_link["href"]
                md5_match = re.search(r"md5=([A-Fa-f0-9]+)", href)
                if md5_match:
                    book.md5 = md5_match.group(1)
                    book.download_url = resolve_download_url(book.md5, mirror)
            results.append(book)
            if len(results) >= limit:
                break
        except (IndexError, ValueError) as e:
            print(f"  [parse] 跳过一行: {e}")
            continue

    return results


def search_libgen_li(query, mirror, limit=10):
    """
    搜索 libgen.li 风格的镜像
    URL: /index.php?req={query}
    """
    search_url = urljoin(
        mirror,
        f"/index.php?req={quote_plus(query)}&columns%5B%5D=t&columns%5B%5D=a"
        f"&objects%5B%5D=f&topics%5B%5D=l&topics%5B%5D=f&res={limit}",
    )
    print(f"  [search] {search_url}")
    resp = try_request(search_url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    table = soup.find("table", {"class": "table"})
    if not table:
        # 尝试找所有表格
        tables = soup.find_all("table")
        if tables:
            table = tables[-1]
    if not table:
        return results

    rows = table.find_all("tr")
    for row in rows[1:]:
        cols = row.find_all("td")
        if len(cols) < 8:
            continue
        try:
            # libgen.li 的列布局与 .is 不同
            book = BookResult(
                title=cols[0].get_text(strip=True) if len(cols) > 0 else "",
                author=cols[1].get_text(strip=True) if len(cols) > 1 else "",
                publisher=cols[2].get_text(strip=True) if len(cols) > 2 else "",
                year=cols[3].get_text(strip=True) if len(cols) > 3 else "",
                language=cols[4].get_text(strip=True) if len(cols) > 4 else "",
                pages=cols[5].get_text(strip=True) if len(cols) > 5 else "",
                size=cols[6].get_text(strip=True) if len(cols) > 6 else "",
                extension=cols[7].get_text(strip=True) if len(cols) > 7 else "",
                md5="",
                mirror=mirror,
            )
            # 查找 MD5
            for link in row.find_all("a"):
                href = link.get("href", "")
                md5_match = re.search(r"md5=([A-Fa-f0-9]+)", href)
                if md5_match:
                    book.md5 = md5_match.group(1)
                    book.download_url = resolve_download_url(book.md5, mirror)
                    break
            results.append(book)
            if len(results) >= limit:
                break
        except (IndexError, ValueError) as e:
            print(f"  [parse] 跳过一行: {e}")
            continue

    return results


def search(query, limit=10):
    """依次尝试所有镜像搜索"""
    for mirror in SEARCH_MIRRORS:
        print(f"\n=== 尝试镜像: {mirror} ===")
        try:
            if "libgen.is" in mirror or "libgen.rs" in mirror or "libgen.bz" in mirror or "libgen.st" in mirror:
                results = search_libgen_is(query, mirror, limit)
            else:
                results = search_libgen_li(query, mirror, limit)

            if results:
                print(f"  找到 {len(results)} 条结果")
                return results
            else:
                print(f"  无结果，尝试下一个镜像...")
        except Exception as e:
            print(f"  镜像 {mirror} 出错: {e}")
            continue

    print("\n所有镜像均无结果")
    return []


# ============================================================
# 下载链接解析
# ============================================================
def resolve_download_url(md5, search_mirror):
    """
    从书籍详情页解析出实际下载链接
    尝试多个下载镜像
    """
    # 方案1: library.lol/main/{md5}
    for dl_mirror in DOWNLOAD_MIRRORS:
        if "library.lol" in dl_mirror:
            detail_url = urljoin(dl_mirror, f"/main/{md5}")
        else:
            detail_url = urljoin(dl_mirror, f"/ads.php?md5={md5}")

        resp = try_request(detail_url)
        if not resp:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        # 查找下载链接 - 多种模式
        # 模式1: <a href="...get.php?md5=...">GET</a>
        for link in soup.find_all("a"):
            href = link.get("href", "")
            text = link.get_text(strip=True).lower()
            if "get.php" in href and ("download" in text or "get" in text):
                return urljoin(dl_mirror, href)
            if href.startswith("http") and (
                "download" in href.lower()
                or ".epub" in href.lower()
                or ".pdf" in href.lower()
            ):
                return href

        # 模式2: 直接从 HTML 正则提取
        match = re.search(r'href="(https?://[^"]*get\.php\?md5=[^"]+)"', resp.text)
        if match:
            return match.group(1)

        match = re.search(r'href="(https?://download\.[^"]+)"', resp.text)
        if match:
            return match.group(1)

    # 方案2: 直接从搜索镜像构造 get.php 链接
    if "libgen.li" in search_mirror or "libgen.lc" in search_mirror:
        return urljoin(search_mirror, f"/get.php?md5={md5}")

    return None


# ============================================================
# 下载书籍文件
# ============================================================
def download_book(book: BookResult) -> BookResult:
    """下载书籍文件"""
    if not book.download_url:
        book.download_status = "failed"
        book.error = "未找到下载链接"
        return book

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    # 安全文件名
    safe_title = re.sub(r'[\\/:*?"<>|]', "_", book.title)[:80]
    filename = f"{safe_title}.{book.extension}" if book.extension else f"{safe_title}.bin"
    filepath = os.path.join(DOWNLOAD_DIR, filename)

    print(f"  [download] {book.title} -> {filepath}")
    print(f"  [download] URL: {book.download_url}")

    resp = try_request(book.download_url, stream=True)
    if not resp:
        book.download_status = "failed"
        book.error = "HTTP 请求失败"
        return book

    # 验证响应内容类型
    content_type = resp.headers.get("Content-Type", "")
    if "text/html" in content_type and not book.download_url.endswith((".pdf", ".epub", ".mobi")):
        # 可能是重定向到错误页
        print(f"  [download] 警告: 响应类型为 HTML，可能不是文件")
        # 继续下载，但标记警告

    total = 0
    with open(filepath, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                total += len(chunk)

    # 验证文件大小
    if total < 1024:
        book.download_status = "failed"
        book.error = f"文件太小 ({total} bytes)，可能是错误页面"
        os.remove(filepath)
        return book

    book.download_status = "success"
    book.download_path = filepath
    print(f"  [download] 成功! {total} bytes")
    return book


# ============================================================
# 主流程
# ============================================================
def main():
    query = os.environ.get("BOOK_QUERY", "")
    if not query:
        if len(sys.argv) > 1:
            query = " ".join(sys.argv[1:])
        else:
            print("错误: 请通过环境变量 BOOK_QUERY 或命令行参数提供搜索关键词")
            sys.exit(1)

    # 可选: 指定格式过滤
    format_filter = os.environ.get("BOOK_FORMAT", "").lower()  # e.g. "pdf", "epub"
    # 可选: 指定下载第几个结果 (1-based)，默认下载第一个
    download_index = int(os.environ.get("DOWNLOAD_INDEX", "1")) - 1
    # 可选: 是否下载所有结果
    download_all = os.environ.get("DOWNLOAD_ALL", "false").lower() == "true"
    # 结果数量
    result_limit = int(os.environ.get("RESULT_LIMIT", "10"))

    print(f"\n{'='*60}")
    print(f"  LibGen 搜索: {query}")
    print(f"  格式过滤: {format_filter or '无'}")
    print(f"  下载目录: {DOWNLOAD_DIR}")
    print(f"{'='*60}\n")

    # 搜索
    results = search(query, limit=result_limit)

    if not results:
        print("\n未找到任何结果")
        with open(RESULTS_FILE, "w") as f:
            json.dump({"query": query, "results": [], "error": "未找到结果"}, f, ensure_ascii=False, indent=2)
        sys.exit(1)

    # 格式过滤
    if format_filter:
        filtered = [r for r in results if r.extension.lower() == format_filter]
        if filtered:
            results = filtered
            print(f"\n格式过滤后剩余 {len(results)} 条结果")

    # 打印搜索结果
    print(f"\n{'='*60}")
    print("  搜索结果:")
    print(f"{'='*60}")
    for i, book in enumerate(results):
        print(f"  [{i+1}] {book.title}")
        print(f"      作者: {book.author}")
        print(f"      格式: {book.extension} | 大小: {book.size} | 年份: {book.year}")
        print(f"      MD5:  {book.md5}")
        print(f"      下载链接: {'有' if book.download_url else '无'}")
        print()

    # 下载
    if download_all:
        to_download = results
    elif download_index < len(results):
        to_download = [results[download_index]]
    else:
        to_download = [results[0]]

    print(f"\n{'='*60}")
    print(f"  开始下载 {len(to_download)} 本书...")
    print(f"{'='*60}\n")

    for book in to_download:
        print(f"\n--- {book.title} ---")
        book = download_book(book)

    # 输出结果 JSON
    output = {
        "query": query,
        "total_results": len(results),
        "downloaded": len([r for r in to_download if r.download_status == "success"]),
        "failed": len([r for r in to_download if r.download_status == "failed"]),
        "results": [asdict(r) for r in results],
    }

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"  完成! 成功: {output['downloaded']}, 失败: {output['failed']}")
    print(f"  结果已保存到: {RESULTS_FILE}")
    print(f"  文件保存在: {DOWNLOAD_DIR}/")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
