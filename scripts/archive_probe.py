#!/usr/bin/env python3
"""云端搜索 archive.org 找漫画理论书的可下载条目"""
import json, subprocess, time

def curl_json(url, timeout=30):
    r = subprocess.run(["curl", "-s", "-L", "--max-time", str(timeout), url],
                       capture_output=True, text=True, timeout=35)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"_err": r.stdout[:200]}

QUERIES = [
    # ===== 漫画理论(已有板块) =====
    ("Making Comics McCloud", 'title:(making comics) AND creator:(mccloud)'),
    ("Manga in Theory and Practice Araki", 'title:(manga in theory and practice)'),
    ("Graphic Storytelling Eisner", 'title:(graphic storytelling) AND creator:(eisner)'),
    ("Comics and Sequential Art Eisner", 'title:(comics and sequential art)'),
    ("Framed Ink Mateu-Mestre", 'title:(framed ink)'),
    # ===== 色彩与光影(新板块) =====
    ("Color and Light Gurney", 'title:(color and light) AND creator:(gurney)'),
    ("Imaginative Realism Gurney", 'title:(imaginative realism)'),
    ("Light for Visual Artists Yot", 'title:(light for visual artists)'),
    ("Interaction of Color Albers", 'title:(interaction of color)'),
    ("Elements of Color Itten", 'title:(elements of color)'),
    ("Art of Color Itten", 'title:(art of color)'),
    ("Vision and Art Livingstone", 'title:(vision and art)'),
    ("Light Science and Magic", 'title:(light science and magic)'),
    ("Digital Lighting and Rendering Birn", 'title:(digital lighting and rendering)'),
    ("Color Workshop Hornung", 'title:(color) AND creator:(hornung)'),
    ("Color Choices Quiller", 'title:(color choices)'),
    ("Color and Meaning Gage", 'title:(color and meaning)'),
]

out = {}
for label, q in QUERIES:
    url = ("https://archive.org/advancedsearch.php?q=" + q.replace(" ", "%20").replace(":", "%3A").replace("(", "%28").replace(")", "%29")
           + "&fl[]=identifier&fl[]=title&fl[]=creator&fl[]=access-restricted-item&fl[]=downloads&rows=8&output=json")
    data = curl_json(url)
    docs = data.get("response", {}).get("docs", [])
    print(f"=== {label} ===", flush=True)
    for d in docs:
        ident = d.get("identifier", "")
        restricted = d.get("access-restricted-item", "?")
        print(f"  {ident} | restricted={restricted} | title={str(d.get('title',''))[:60]}", flush=True)
    out[label] = docs
    time.sleep(2)

# 对候选identifier拉metadata看文件列表(只拉前几个)
print("\n=== 文件列表探测 ===", flush=True)
for label, docs in out.items():
    for d in docs[:3]:
        ident = d.get("identifier", "")
        if not ident:
            continue
        md = curl_json(f"https://archive.org/metadata/{ident}", timeout=30)
        files = md.get("files", [])
        pdfs = [f["name"] for f in files if f["name"].lower().endswith(".pdf") or f["name"].lower().endswith(".txt") or f["name"].lower().endswith(".epub")]
        restricted = md.get("metadata", {}).get("access-restricted-item", "?")
        print(f"{ident}: restricted={restricted} files={pdfs[:6]}", flush=True)
        time.sleep(1)

with open("/tmp/archive_probe.json", "w") as f:
    json.dump(out, f, ensure_ascii=False)
print("\nDONE")
