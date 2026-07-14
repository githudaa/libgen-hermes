# LibGen-Hermes: 通过 GitHub Actions 自动搜书下载

让 hermes（或任何外部系统）通过 GitHub API 触发 LibGen 搜索和下载，绕过本地网络拦截。

## 架构原理

```
hermes (你的 AI/bot)
    │
    │  1. POST /repos/USER/REPO/dispatches
    │     (通过 GitHub API 触发)
    ▼
┌──────────────────────────┐
│   GitHub Actions Runner   │
│   (GitHub 云服务器)        │
│                           │
│   2. 访问 LibGen 镜像      │
│   3. 搜索书籍              │
│   4. 解析下载链接           │
│   5. 下载书籍文件           │
│   6. 上传为 Artifact       │
└──────────┬───────────────┘
           │
    7. hermes 轮询 run 状态
    8. hermes 下载 Artifact (ZIP)
    9. 解压得到书籍文件
           │
           ▼
    hermes 拿到书籍文件 ✅
```

**核心思路**: GitHub Actions 的服务器 IP 不被 LibGen 拦截，所以把搜索和下载放到 GitHub 上执行，hermes 只需调 API + 下载结果。

---

## 快速开始

### 1. Fork / 创建仓库

把 `libgen-hermes/` 目录的文件推到你的 GitHub 仓库:

```bash
cd libgen-hermes
git init
git add .
git commit -m "LibGen Hermes 自动搜书下载"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/libgen-hermes.git
git push -u origin main
```

### 2. 创建 GitHub Token

1. 打开 https://github.com/settings/tokens?type=beta (Fine-grained token)
2. 点击 "Generate new token"
3. 设置:
   - Token name: `hermes-libgen`
   - Repository access: 仅选中你的 `libgen-hermes` 仓库
   - Permissions:
     - **Actions**: Read and write
     - **Contents**: Read-only
4. 生成后复制 Token

### 3. 配置 hermes 端环境变量

```bash
export GITHUB_TOKEN=github_pat_xxxxx
export GITHUB_OWNER=your_username
export GITHUB_REPO=libgen-hermes
```

### 4. 测试搜索下载

```bash
# 方式 A: 直接运行 hermes_api.py (一站式)
python scripts/hermes_api.py "深入理解计算机系统" pdf 1

# 方式 B: 手动触发 GitHub Actions
# 去 GitHub 仓库 -> Actions -> "LibGen 搜书下载" -> Run workflow
# 填入搜索关键词，等待完成后在 Artifacts 区域下载
```

---

## 在 hermes 代码中集成

### Python 集成

```python
import sys
sys.path.insert(0, "path/to/libgen-hermes/scripts")
from hermes_api import search_and_download

# 用户说 "帮我找一本《深入理解计算机系统》的 PDF"
result = search_and_download(
    query="深入理解计算机系统",
    fmt="pdf",           # 可选: pdf / epub / mobi
    download_index=1,    # 下载第一个结果
    output_dir="./books"  # 下载到这个目录
)

if result["success"]:
    print(f"下载完成! 文件在: {result['output_dir']}")
    # 展示搜索结果给用户
    for book in result.get("results", {}).get("results", []):
        print(f"  - {book['title']} ({book['extension']}, {book['size']})")
else:
    print(f"搜索失败: {result.get('error')}")
```

### 直接调 GitHub API (适用于非 Python 环境)

**触发搜索:**
```bash
curl -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/repos/$GITHUB_OWNER/libgen-hermes/dispatches \
  -d '{
    "event_type": "search_book",
    "client_payload": {
      "query": "深入理解计算机系统",
      "format": "pdf",
      "download_index": "1",
      "result_limit": "10"
    }
  }'
```

**查询状态:**
```bash
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/$GITHUB_OWNER/libgen-hermes/actions/runs?event=repository_dispatch&per_page=1" \
  | jq '.workflow_runs[0] | {id, status, conclusion}'
```

**下载 Artifact:**
```bash
# 获取 artifact 列表
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/$GITHUB_OWNER/libgen-hermes/actions/runs/RUN_ID/artifacts" \
  | jq '.artifacts[] | {id, name}'

# 下载 (返回 ZIP)
curl -L -H "Authorization: Bearer $GITHUB_TOKEN" \
  -o books.zip \
  "https://api.github.com/repos/$GITHUB_OWNER/libgen-hermes/actions/artifacts/ARTIFACT_ID/zip"

# 解压
unzip books.zip -d books/
```

---

## 工作流参数说明

| 参数 | 环境变量 | 说明 | 默认值 |
|------|---------|------|--------|
| 搜索关键词 | `BOOK_QUERY` | 书名/作者/主题 | 必填 |
| 格式过滤 | `BOOK_FORMAT` | pdf/epub/mobi，留空不过滤 | 空 |
| 下载索引 | `DOWNLOAD_INDEX` | 1=第一个结果，0=全部 | 1 |
| 结果数量 | `RESULT_LIMIT` | 搜索返回多少条 | 10 |
| 下载目录 | `DOWNLOAD_DIR` | 文件保存路径 | ./downloads |
| 结果文件 | `RESULTS_FILE` | JSON 结果路径 | ./results.json |

---

## LibGen 镜像说明

脚本内置了多个镜像，按优先级自动尝试:

| 镜像 | 搜索端点 | 备注 |
|------|---------|------|
| libgen.is | `/search.php` | 主站 |
| libgen.rs | `/search.php` | 镜像 |
| libgen.li | `/index.php` | 不同页面结构 |
| libgen.st | `/search.php` | 镜像 |
| libgen.bz | `/search.php` | 镜像 |

下载链接解析支持:
- `library.lol/main/{md5}` - 详情页解析
- `libgen.li/ads.php?md5={md5}` - 详情页解析
- `libgen.li/get.php?md5={md5}` - 直接下载

如果所有镜像都不可用，脚本会在 `results.json` 中标记错误。

---

## 常见问题

### Q: GitHub Actions 的 artifact 下载下来是 ZIP，怎么自动解压？
`hermes_api.py` 的 `download_artifact()` 已经内置了 ZIP 解压逻辑，直接用就行。

### Q: Artifact 保留多久？
默认 7 天。可以在 workflow 中修改 `retention-days`。

### Q: 搜索没结果怎么办？
1. 检查关键词是否太短（LibGen 要求至少 3 个字符）
2. 尝试用英文搜索
3. 检查镜像状态: https://open-slum.org/
4. 在 GitHub Actions 日志中查看哪个镜像被尝试了

### Q: 下载失败怎么办？
1. 查看 `results.json` 中的 `download_status` 和 `error` 字段
2. 文件太小（<1KB）通常意味着下载到了错误页面
3. 尝试换一个 `download_index` 下载其他结果
4. 尝试不指定格式（有些书只有特定格式）

### Q: 可以自动推送到 Kindle 吗？
可以！在 workflow 中加一个步骤，用 `kindle` 邮箱推送:
```yaml
- name: Send to Kindle
  run: |
    pip install kindle
    kindle send --email ${{ secrets.KINDLE_EMAIL }} --file downloads/*.epub
```

### Q: 如何限制只有 hermes 能触发？
在 `repository_dispatch` 的 `client_payload` 中加一个 secret token，在 workflow 第一步验证:
```yaml
- name: Verify token
  run: |
    if [ "${{ github.event.client_payload.token }}" != "${{ secrets.HERMES_TOKEN }}" ]; then
      echo "Unauthorized"
      exit 1
    fi
```

---

## 文件结构

```
libgen-hermes/
├── scripts/
│   ├── libgen_search.py    # 核心搜索下载脚本 (运行在 GitHub Actions)
│   └── hermes_api.py       # hermes 端 API 调用辅助脚本
├── .github/
│   └── workflows/
│       └── libgen.yml      # GitHub Actions 工作流
├── requirements.txt
└── README.md
```
