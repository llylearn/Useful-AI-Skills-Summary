#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查汇总包结构、文本、Python、JSON、排除项和 SHA-256。"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys

EXPECTED = {
    "dsh-tui-guide",
    "explain-code",
    "smart-sensing-youth-post",
    "weekly-report",
    "history-combo-derive",
    "lianban-duizhao",
}
REQUIRED = {
    "dsh-tui-guide": ["configuration.md", "user-guide.md"],
    "explain-code": ["使用说明.md"],
    "smart-sensing-youth-post": ["使用说明.md"],
    "weekly-report": ["使用说明.md"],
    "history-combo-derive": [
        "使用说明.md", "pipeline/derive.py", "pipeline/report_html.py",
        "pipeline/requirements.txt", "pipeline/data/day_20261111.json",
        "pipeline/data/em_20261111.json",
    ],
    "lianban-duizhao": [
        "使用说明.md", "pipeline/fetch_kaipan.py", "pipeline/fetch_current.py",
        "pipeline/fetch_kaipan_detail.py", "pipeline/fetch_concepts.py",
        "pipeline/compare_section.py", "pipeline/build.py", "pipeline/check.py",
        "pipeline/browser_check.py", "pipeline/template.html", "pipeline/README.md",
        "pipeline/requirements.txt", "pipeline/kaipan_history.json",
        "pipeline/current_pool.json", "pipeline/section_data.json",
    ],
}
TEXT_SUFFIXES = {".md", ".py", ".txt", ".ps1", ".html"}
FORBIDDEN_TEXT = ("C:\\Users\\" + "11690", "C:\\Users\\" + "李力源", "/home/" + "liliyuan")


def package_files(root):
    return sorted((p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS"),
                  key=lambda p: p.relative_to(root).as_posix())


def write_manifest(root, files):
    lines = []
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(digest + "  " + path.relative_to(root).as_posix())
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("已生成 SHA256SUMS：{} 个文件".format(len(lines)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-manifest", action="store_true", help="完成预检后重建 SHA256SUMS")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    errors = []
    for name in sorted(EXPECTED):
        skill = root / name
        for required in ["SKILL.md", "README.md"] + REQUIRED.get(name, []):
            if not (skill / required).exists():
                errors.append("缺少资产：{}/{}".format(name, required))
        skill_md = skill / "SKILL.md"
        if skill_md.is_file():
            text = skill_md.read_text(encoding="utf-8")
            if not text.startswith("---\n") or "\nname: " not in text:
                errors.append("frontmatter 异常：" + name)

    files = package_files(root)
    python_count = json_count = 0
    for path in files:
        rel = path.relative_to(root)
        parts = rel.parts
        if path.name == "SKILL.original.md" or path.suffix == ".pyc":
            errors.append("包含应排除文件：" + rel.as_posix())
        if any(part == "__pycache__" or part == ".venv" or part.startswith((".chrome-cdp", ".chrome-shot-")) for part in parts):
            errors.append("包含缓存或浏览器配置：" + rel.as_posix())
        if path.name.lower() in {"login data", "cookies", "history"}:
            errors.append("包含疑似浏览器个人数据：" + rel.as_posix())
        if path.parent.name == "pipeline" and path.suffix == ".html" and path.name.startswith(("对比看板_", "历史组合_")):
            errors.append("包含生成的旧报告：" + rel.as_posix())
        if path.suffix == ".py":
            python_count += 1
            try:
                ast.parse(path.read_text(encoding="utf-8-sig"), filename=rel.as_posix())
            except (SyntaxError, UnicodeError) as exc:
                errors.append("Python 语法/编码错误 {}：{}".format(rel.as_posix(), exc))
        elif path.suffix == ".json":
            json_count += 1
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (ValueError, UnicodeError) as exc:
                errors.append("JSON 错误 {}：{}".format(rel.as_posix(), exc))
        if path.suffix in TEXT_SUFFIXES:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeError as exc:
                errors.append("文本编码错误 {}：{}".format(rel.as_posix(), exc))
            else:
                for old_path in FORBIDDEN_TEXT:
                    if old_path in text:
                        errors.append("包含原机个人路径 {}：{}".format(old_path, rel.as_posix()))

    if not args.write_manifest:
        manifest = root / "SHA256SUMS"
        if not manifest.is_file():
            errors.append("缺少 SHA256SUMS；有意修改包后可运行 --write-manifest")
        else:
            listed = set()
            for line_no, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    expected_hash, rel_text = line.split(None, 1)
                    rel_text = rel_text.strip()
                    rel = Path(rel_text)
                    if rel.is_absolute() or ".." in rel.parts or rel_text in listed:
                        raise ValueError("非法或重复相对路径")
                    path = root / rel
                    actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
                    if actual_hash != expected_hash:
                        errors.append("SHA-256 不匹配：" + rel_text)
                    listed.add(rel_text)
                except (ValueError, OSError) as exc:
                    errors.append("SHA256SUMS 第 {} 行错误：{}".format(line_no, exc))
            actual = {p.relative_to(root).as_posix() for p in files}
            for missing in sorted(listed - actual):
                errors.append("哈希清单引用不存在文件：" + missing)
            for extra in sorted(actual - listed):
                errors.append("文件未纳入哈希清单：" + extra)

    if errors:
        print("验收失败，共 {} 项：".format(len(errors)), file=sys.stderr)
        for error in errors:
            print("- " + error, file=sys.stderr)
        return 1
    if args.write_manifest:
        write_manifest(root, files)
    print("验收通过")
    print("- 技能：{} 个".format(len(EXPECTED)))
    print("- 文件：{} 个（不含 SHA256SUMS）".format(len(files)))
    print("- Python 脚本语法：{} 个".format(python_count))
    print("- JSON 数据：{} 个".format(json_count))
    print("- 未发现个人旧路径、浏览器配置、.venv、__pycache__ 或生成的旧报告")
    return 0


if __name__ == "__main__":
    sys.exit(main())
