# Useful AI Skills Summary

整理日期：2026-11-11。此包汇总当前使用的 **6 个 Skill**，每个技能都有独立目录、完整 `SKILL.md`、中文 `README.md`，以及运行所需的脚本、模板、依赖清单或离线数据。

## 技能总览

| 技能 | 用途与触发示例 | 运行依赖 |
|---|---|---|
| `dsh-tui-guide` | 查询 dsh-tui 用法、配置、主题、迁移、CLI、VS Code 等 | 无第三方依赖；含中英文手册 |
| `explain-code` | “讲解代码”“逐行解释这个文件”，以前端转后端视角讲代码 | 无 |
| `smart-sensing-youth-post` | “青年突击队推文”“智能感知项目宣传稿” | 无；事实不足时标【待补充】 |
| `weekly-report` | 提供工作记录并要求“生成个人周报” | 无；仅明确要求时写 TXT |
| `history-combo-derive` | “历史组合”“首板历史组合”，生成首板历史同日组合报告 | Python 3.8+、requests、Markdown、chardet；最新数据需网络 |
| `lianban-duizhao` | “对比看板”“更新今日对照看板” | Python 3.8+、requests、websocket-client、chardet；最新数据需网络，验收需 Chrome |

这 6 个技能均来自本机 `~/.dsh/skills`。

## 目录约定

```text
Useful-AI-Skills-Summary/
├── README.md
├── install.py                 # 直接扫描各一级技能目录
├── verify_package.py          # 结构、语法、JSON、隐私路径和 SHA-256 校验
├── SHA256SUMS
├── dsh-tui-guide/
├── explain-code/
├── smart-sensing-youth-post/
├── weekly-report/
├── history-combo-derive/
└── lianban-duizhao/
```

每个技能根目录都应有 `SKILL.md` 和 `README.md`。A 股技能的脚本与数据位于各自 `pipeline/`；诊断脚本位于 `scripts/`。

## 迁移与安装

1. 将整个 `Useful-AI-Skills-Summary` 文件夹复制到新机器。
2. 阅读根目录和各技能的 `README.md`，特别是桌面、Chrome、交易日和权限注意事项。
3. 确认 Python 3.8+ 可用，在本目录执行：

```powershell
# 预览，不写文件
python install.py --with-deps --dry-run

# 安装到默认 ~/.dsh/skills，并创建共享虚拟环境、安装依赖
python install.py --with-deps
```

若 Windows 安装了 `py` 启动器，也可用 `py -3 install.py --with-deps`。可用 `--target <目录>` 改安装位置。同名技能默认跳过；只有明确要合并覆盖时才加 `--force`，目标目录中的额外文件不会被删除。

4. 重新扫描技能或新开 DSH 会话，用 `/skills` 逐项确认。
5. 在目标机重新创建依赖环境；不要复制原机 `.venv`。

## 必须重新本地化

- **桌面输出**：A 股脚本与周报落盘使用 `DESKTOP_DIR`。它是完整输出目录，不应照抄原电脑路径；例如 PowerShell 设置 `$env:DESKTOP_DIR = 'D:\实际目录\临时文件'`。
- **Python**：Windows 虚拟环境解释器为 `~/.dsh/skills/.venv/Scripts/python.exe`，Linux/macOS 为 `.venv/bin/python`。
- **Chrome**：看板浏览器验收前安装 Chrome/Chromium，并将 `CHROME_BIN` 指向实际程序；不要默认添加 `--no-sandbox`。
- **交易日**：`lianban-duizhao` 每日使用前更新 `fetch_kaipan.py` 的 `END/CUR_DATE`、`fetch_current.py` 的 `CUR_DATE`、`compare_section.py` 的 `CUR_DATE`。`END` 是前一交易日，不能误写为尚未发布数据的当天。
- **dsh-tui 手册**：新版本软件以目标机自带手册为准，本包是 2026-11-11 的参考快照。

## 校验与安全恢复

```powershell
# 只读完整性检查
python verify_package.py

# 对 history-combo-derive 做离线重建示例（输出到临时目录）
& "$HOME\.dsh\skills\.venv\Scripts\python.exe" `
  "$HOME\.dsh\skills\history-combo-derive\pipeline\derive.py" `
  --date 20261111 --no-fetch --out "$env:TEMP\skills-check\history"

# lianban-duizhao 可先用缓存执行 build.py、check.py、browser_check.py；
# 运行前把 DESKTOP_DIR 指向临时验收目录，避免覆盖正式报告。
```

若有意修改了包内文件，先确认修改正确，再运行 `python verify_package.py --write-manifest` 重建哈希清单，随后再运行一次只读校验。

## 保留与排除

保留了当前生效的技能定义、最新看板定版规则、脚本、模板、中英文手册、离线 JSON 数据和迁移说明。排除了 `.venv`、`__pycache__`、`.pyc`、Chrome profile、浏览器历史／登录数据、生成的旧 HTML 报告及凭据。

A 股缓存只是历史快照，不代表迁移当天的数据；报告仅用于历史复盘，不构成投资建议。
