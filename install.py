#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""安装当前目录下的一级技能目录，并可重建共享 Python 环境。"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys


def parse_args():
    default_target = os.environ.get("DSH_SKILLS_DIR", str(Path.home() / ".dsh" / "skills"))
    parser = argparse.ArgumentParser(description="安装汇总包中的全部技能；同名技能默认跳过。")
    parser.add_argument("--target", default=default_target, help="技能安装目录，默认 ~/.dsh/skills")
    parser.add_argument("--with-deps", action="store_true", help="创建 .venv 并安装各技能 requirements.txt")
    parser.add_argument("--force", action="store_true", help="合并覆盖同名文件，不删除目标额外文件")
    parser.add_argument("--dry-run", action="store_true", help="只显示计划，不写文件、不安装依赖")
    return parser.parse_args()


def discover_skills(root):
    skills = []
    for source in sorted(root.iterdir(), key=lambda p: p.name):
        if source.is_dir() and not source.name.startswith(".") and (source / "SKILL.md").is_file():
            skills.append(source)
    if not skills:
        raise RuntimeError("未发现 <技能目录>/SKILL.md；请在汇总包根目录运行")
    names = [p.name for p in skills]
    if len(names) != len(set(names)):
        raise RuntimeError("技能目录名重复")
    return skills


def venv_python(venv_dir):
    return venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def copy_ignore(directory, names):
    ignored = []
    for name in names:
        if name == "__pycache__" or name == ".venv" or name.startswith((".chrome-cdp", ".chrome-shot-")):
            ignored.append(name)
        elif name.endswith(".pyc") or name == "SKILL.original.md":
            ignored.append(name)
    return ignored


def install_dependencies(target, skills, dry_run):
    venv_dir = target / ".venv"
    python = venv_python(venv_dir)
    requirements = []
    for source in skills:
        installed_req = target / source.name / "pipeline" / "requirements.txt"
        source_req = source / "pipeline" / "requirements.txt"
        req = installed_req if installed_req.exists() else source_req
        if req.exists() and req not in requirements:
            requirements.append(req)
    if dry_run:
        print("[DRY-RUN] 创建虚拟环境：", venv_dir)
        for req in requirements:
            print("[DRY-RUN] 安装依赖：", req)
        return
    if not python.exists():
        print("创建虚拟环境：", venv_dir)
        subprocess.check_call([sys.executable, "-m", "venv", str(venv_dir)])
    for req in requirements:
        print("安装依赖：", req)
        subprocess.check_call([str(python), "-m", "pip", "install", "-r", str(req)])
    print("Python 解释器：", python)


def main():
    if sys.version_info < (3, 8):
        raise RuntimeError("需要 Python 3.8+")
    args = parse_args()
    root = Path(__file__).resolve().parent
    target = Path(args.target).expanduser().resolve()
    skills = discover_skills(root)
    print("汇总包：", root)
    print("安装到：", target)
    print("发现技能：", len(skills), "个")
    installed, skipped = [], []
    for source in skills:
        destination = target / source.name
        if destination.exists() and not args.force:
            skipped.append(source.name)
            print("SKIP（已存在；--force 可合并覆盖）：", source.name)
            continue
        if args.dry_run:
            print("[DRY-RUN] 复制：", source, "->", destination)
        else:
            target.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, destination, dirs_exist_ok=True, ignore=copy_ignore)
        installed.append(source.name)
        print("OK：", source.name)
    if args.with_deps:
        install_dependencies(target, skills, args.dry_run)
    print("\n完成：计划/已安装 {} 个，跳过 {} 个。".format(len(installed), len(skipped)))
    if skipped:
        print("跳过列表：" + ", ".join(skipped))
    print("下一步：重新扫描技能或新开 DSH 会话，用 /skills 检查。")
    print("桌面、Chrome 和交易日必须按目标机重新本地化。")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print("安装失败：{}".format(exc), file=sys.stderr)
        sys.exit(1)
