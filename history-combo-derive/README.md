# history-combo-derive

## 用途

把当前首板股与近一年历史首板日求交集，寻找“同一天一起首板”的组合，追踪该梯队后来走出的 4 连板及以上个股，并输出七段式单文件 HTML。触发词包括“历史组合”“首板历史组合”“同日首板组合”。

## 目录与依赖

- `SKILL.md`、`使用说明.md`：口径、流程和验收规则。
- `pipeline/derive.py`：抓数、分析、建模、渲染和归档。
- `pipeline/report_html.py`：自包含 HTML 渲染。
- `pipeline/fetch_all.py`、`analyze.py`：旧版兜底脚本，运行前必须检查日期。
- `pipeline/data/`：历史 JSON 缓存，本包快照更新至 2026-11-11。
- `pipeline/requirements.txt`：requests、Markdown、chardet。

## 恢复与运行

通过根目录 `install.py --with-deps` 恢复共享环境，或在新环境安装 requirements。Windows 示例：

```powershell
$PY = "$HOME\.dsh\skills\.venv\Scripts\python.exe"
& $PY "$HOME\.dsh\skills\history-combo-derive\pipeline\derive.py" --out 'D:\实际输出目录'
# 离线验收已有缓存
& $PY "$HOME\.dsh\skills\history-combo-derive\pipeline\derive.py" --date 20261111 --no-fetch --out "$env:TEMP\history-check"
```

正式输出为 `历史组合_<YYYYMMDD>.html`，主输出与 `pipeline/output` 归档必须哈希一致。最新数据需要访问东方财富和同花顺；离线缓存不代表迁移当天。首板和 4 板+口径不得擅改，历史结果不是未来预测，不构成投资建议。
