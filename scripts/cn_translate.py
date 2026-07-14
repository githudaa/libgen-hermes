#!/usr/bin/env python3
"""
中文教材书名 → 英文 LibGen 搜索词 翻译引擎

策略：
  L1: 精确映射表（硬编码已知教材的英文名）
  L2: 关键词提取（出版社/作者名转英文）
  L3: 通用兜底（去掉中文限定词，保留核心概念词）

用法:
  from cn_translate import translate
  queries = translate("陈阅增普通生物学（第4版）")
  # -> ["General Biology Chen Yuezeng", "Chen Yue Zeng General Biology 4th"]
"""

import re

# ═══════════════════════════════════════════════════
# L1: 精确映射表
# 格式: 中文书名 -> [英文搜索词列表，按优先级排列]
# ═══════════════════════════════════════════════════

TEXTBOOK_MAP = {
    # === 生物学 ===
    "陈阅增普通生物学": [
        "General Biology Chen Yuezeng",
        "Chen Yue Zeng General Biology",
        "General Biology 4th edition",
    ],
    "基础生命科学": [
        "Fundamentals of Life Science Wu Qingyu",
        "Basic Life Science textbook",
        "Life Science fundamentals",
    ],
    "Campbell生物学": [
        "Campbell Biology",
        "Campbell Biology Urry",
        "Campbell Biology 11th edition",
    ],
    "生物学": [
        "Biology textbook 6th edition Wang Bin",
        "Biology Zuo Mingxue",
    ],
    "普通生物学": [
        "General Biology textbook",
        "General Biology Campbell",
    ],
    "生命是什么": [
        "What is Life Schrodinger",
        "What is Life physical aspect",
    ],
    "双螺旋": [
        "The Double Helix Watson",
        "Double Helix personal account",
    ],

    # === 生物化学 ===
    "生物化学": [
        "Biochemistry Wang Jingyan",
        "Biochemistry 4th edition textbook",
        "Biochemistry Zhu Shengeng",
        "Biochemistry Lehninger",
    ],
    "生物化学原理": [
        "Principles of Biochemistry Yang Rongwu",
        "Principles of Biochemistry textbook",
        "Biochemistry principles",
    ],
    "Lehninger生物化学": [
        "Lehninger Principles of Biochemistry",
        "Lehninger Biochemistry",
        "Lehninger Principles Biochemistry 8th Nelson",
    ],

    # === 化学 ===
    "普通化学": [
        "General Chemistry textbook",
        "General Chemistry principles",
    ],
    "有机化学": [
        "Organic Chemistry textbook",
        "Organic Chemistry clayden",
    ],
    "物理化学": [
        "Physical Chemistry textbook",
        "Physical Chemistry Atkins",
    ],
    "无机化学": [
        "Inorganic Chemistry textbook",
        "Inorganic Chemistry Shriver",
    ],
    "分析化学": [
        "Analytical Chemistry textbook",
        "Analytical Chemistry Harris",
    ],

    # === 物理学 ===
    "普通物理学": [
        "University Physics textbook",
        "Fundamentals of Physics Halliday",
        "Physics for Scientists and Engineers",
    ],
    "固体物理学": [
        "Solid State Physics textbook",
        "Introduction to Solid State Physics Kittel",
    ],
    "半导体物理学": [
        "Semiconductor Physics textbook",
        "Physics of Semiconductor Devices",
        "Semiconductor Device Fundamentals",
    ],
    "量子力学": [
        "Quantum Mechanics textbook",
        "Introduction to Quantum Mechanics Griffiths",
        "Quantum Mechanics Sakurai",
    ],
    "热力学与统计物理": [
        "Thermal Physics textbook",
        "Thermodynamics statistical mechanics",
        "Thermal Physics Blatt",
    ],
    "电动力学": [
        "Electrodynamics textbook",
        "Classical Electrodynamics Jackson",
        "Introduction to Electrodynamics Griffiths",
    ],

    # === 数学 ===
    "高等数学": [
        "Advanced Mathematics textbook",
        "Calculus textbook",
        "Thomas Calculus",
    ],
    "线性代数": [
        "Linear Algebra textbook",
        "Linear Algebra done right",
        "Introduction to Linear Algebra Strang",
    ],
    "概率论与数理统计": [
        "Probability and Statistics textbook",
        "Introduction to Probability",
    ],
    "数学分析": [
        "Mathematical Analysis textbook",
        "Principles of Mathematical Analysis Rudin",
    ],

    # === 计算机 ===
    "数据结构": [
        "Data Structures textbook",
        "Data Structures and Algorithms",
    ],
    "计算机组成原理": [
        "Computer Organization textbook",
        "Computer Organization and Design",
    ],
    "操作系统": [
        "Operating Systems textbook",
        "Operating System Concepts",
    ],
    "计算机网络": [
        "Computer Networks textbook",
        "Computer Networking Kurose",
    ],
    "深入理解计算机系统": [
        "Computer Systems A Programmer's Perspective",
        "CSAPP",
    ],
}

# ═══════════════════════════════════════════════════
# 中文→英文 关键词映射
# ═══════════════════════════════════════════════════

KEYWORD_MAP = {
    "导论": "introduction",
    "概论": "introduction",
    "原理": "principles",
    "基础": "fundamentals",
    "高级": "advanced",
    "现代": "modern",
    "简明": "concise",
    "教程": "course",
    "习题": "solutions",
    "实验": "laboratory",
    "第1版": "1st edition",
    "第2版": "2nd edition",
    "第3版": "3rd edition",
    "第4版": "4th edition",
    "第5版": "5th edition",
    "第6版": "6th edition",
    "第7版": "7th edition",
    "第8版": "8th edition",
    "第9版": "9th edition",
    "第10版": "10th edition",
    "第11版": "11th edition",
    "上册": "volume 1",
    "下册": "volume 2",
    "上下册": "complete",
}

# ═══════════════════════════════════════════════════
# 翻译函数
# ═══════════════════════════════════════════════════

def _clean_title(cn_title: str) -> str:
    """清理书名，去掉括号版本号等"""
    # 去掉括号内容（但保留有用的）
    title = re.sub(r'[（(][^)）]*[)）]', ' ', cn_title)
    # 去掉多余空格
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def _extract_core(cn_title: str) -> str:
    """提取核心学科名（最长匹配）"""
    clean = _clean_title(cn_title)
    # 按长度降序尝试匹配
    for key in sorted(TEXTBOOK_MAP.keys(), key=len, reverse=True):
        if key in clean:
            return key
    return clean


def translate(cn_title: str, author: str = "", publisher: str = "") -> list:
    """
    中文教材名 → 英文 LibGen 搜索词列表

    参数:
        cn_title: 中文书名
        author: 作者名（可选，用于提高精度）
        publisher: 出版社（可选）

    返回:
        list[str]: 英文搜索词列表，按优先级排列
    """
    queries = []

    # L1: 精确映射
    core = _extract_core(cn_title)
    if core in TEXTBOOK_MAP:
        queries.extend(TEXTBOOK_MAP[core])

    # L2: 基于作者+关键词构造
    if author and not queries:
        # 提取作者姓氏拼音
        author_simple = author.split("/")[0].split("、")[0].strip() if author else ""
        if author_simple:
            # 尝试加作者名的搜索
            queries.append(f"{core} {author_simple}")

    # L3: 关键词替换
    clean = _clean_title(cn_title)
    for cn, en in KEYWORD_MAP.items():
        if cn in clean:
            clean = clean.replace(cn, en)
    # 去掉残留中文
    clean = re.sub(r'[\u4e00-\u9fff]+', '', clean).strip()
    if clean and clean not in queries:
        queries.append(clean)

    # 去重保序
    seen = set()
    result = []
    for q in queries:
        q = q.strip()
        if q and q not in seen and len(q) > 3:
            seen.add(q)
            result.append(q)

    return result if result else [cn_title]


# ═══════════════════════════════════════════════════
# 批量翻译（从xlsx/tsv读取）
# ═══════════════════════════════════════════════════

def translate_from_row(row: dict) -> list:
    """从表格行数据翻译"""
    title = row.get("书名", row.get("title", ""))
    author = row.get("作者", row.get("author", ""))
    publisher = row.get("出版社", row.get("publisher", ""))
    return translate(title, author, publisher)


# ═══════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        title = sys.argv[1]
        author = sys.argv[2] if len(sys.argv) > 2 else ""
        queries = translate(title, author)
        print(f"\n中文: {title}")
        print(f"英文搜索词:")
        for i, q in enumerate(queries):
            print(f"  [{i+1}] {q}")
    else:
        # Test
        tests = [
            "陈阅增普通生物学（第4版）",
            "基础生命科学（第2版）",
            "Campbell生物学（第11版）",
            "量子力学教程",
            "固体物理学",
            "高等数学（第7版，上下册）",
            "深入理解计算机系统",
        ]
        for t in tests:
            queries = translate(t)
            print(f"\n{t}")
            for q in queries:
                print(f"  -> {q}")
