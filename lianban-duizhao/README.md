# lianban-duizhao

## 用途

生成“对比看板／连板对照看板”：把当前涨停池与历史共同涨停日按板数逐行对齐。版式取自本地 mac 看板：hero 5 张统计卡、对照区大标题/七宫格、共同涨停胶囊、吸顶双栏头、居中板数轴；卡片显示行业、地域、领涨概念／历史原因、封单金额/手数、同梯队战绩和终 N 板，点击卡片打开详情弹窗。

## 当前定版（2026-11-12）

- 整页版式对齐本地 mac 看板：hero 标题 + 5 张统计卡（当前涨停/当前晋级/最高连板/共同涨停/重合率）；
  对照区「共同涨停 N 只 · 重合率」+ 七宫格 + 共同涨停胶囊 + 吸顶双栏头 + 居中板数轴。
- 所有卡片白底；共同股仅用 **2px 蓝框 `#356b9a`**，普通卡片 1px；当前侧 3px 琥珀、历史侧 3px 靛蓝左缘。
- 地域蓝色、行业琥珀色、概念／历史原因橙色 `#ffedd5 / #c2410c`；历史共同卡「终N板」用紫色徽标。
- 地域／输赢／终N板行下、概念行上有独立 `.seal` 行：`封单 金额 / 手数`。
- 手数＝收盘封单额 ÷ 当日收盘价 ÷ 100，是换算约值；缺数据用 `—`，不得编造。
- 2026-11-11 构建可复现：322 卡 / 42 共同卡 / 21 枚共同胶囊 / 21 枚终N板；1440 4 列、390 1 列，无横向溢出。

## 目录与依赖

`pipeline/` 包含抓数、详情、概念、比较、构建、Python 自检、Chrome 验收脚本，以及模板、requirements、README 和离线 JSON。依赖 requests、websocket-client、chardet；浏览器验收另需 Chrome/Chromium。历史池共 1660 个交易日，扫描至 2026-11-10；当前快照为 2026-11-11。

## 每日更新

先修改三处日期：`fetch_kaipan.py` 的 `END/CUR_DATE`、`fetch_current.py` 的 `CUR_DATE`、`compare_section.py` 的 `CUR_DATE`，再依次执行：

```powershell
Set-Location "$HOME\.dsh\skills\lianban-duizhao\pipeline"
$PY = "$HOME\.dsh\skills\.venv\Scripts\python.exe"
& $PY fetch_kaipan.py
& $PY fetch_current.py
& $PY compare_section.py
# 若提示缺详情，先执行 fetch_kaipan_detail.py "<对照日>"，再重跑 compare_section.py
& $PY fetch_concepts.py
& $PY compare_section.py
& $PY build.py
& $PY check.py
& $PY browser_check.py
```

运行前设置真实 `DESKTOP_DIR` 和 `CHROME_BIN`。`END` 必须是前一交易日；接口无数据、限流或字段缺失时如实留空，不能伪造概念、地域、行业或封单。成品为 `对比看板_<YYYY-MM-DD>.html`，桌面与项目归档必须哈希一致。历史复盘不构成投资建议。
