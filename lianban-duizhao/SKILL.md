---
name: lianban-duizhao
description: 生成「对比看板 / 连板对照看板」——A 股当前涨停股与历史共同涨停日逐板对齐的单文件 HTML；采用本地 mac 看板的 hero 统计卡、对照区七宫格、共同涨停胶囊、吸顶双栏头与居中板数轴，白底卡片以蓝/琥珀/橙色 tag 展示地域、行业和领涨概念，共同股用 2px 蓝框，地域行下显示收盘封单金额/手数；点开看首封/封单/炸板/几天几板与同梯队晋级战绩、终N板；含开盘啦多年历史池、周期排除、东财限流兜底与验收方法。
whenToUse: 用户说「对比看板」「连板对照看板」「更新今日对照看板」时使用；用于按本地 mac 看板版式生成 A 股当前涨停股与历史共同涨停日的逐板对照页。
---

# 今日对照 · A 股连板历史对照页

> 触发词：**对比看板**（别名：连板对照看板、更新今日对照看板）。用户说出这句话时，直接按本 skill 执行。

把「当前交易日涨停池」和「历史某日涨停池」按连板数左右对齐：同一行同一板数，
共同涨停高亮，点卡片看首封、封单、炸板、几天几板，以及同梯队 3 板+ 的赢/输对手。

当前本机实现：`~/.dsh/skills/lianban-duizhao/pipeline/`（Windows，Python 3.8+；共享解释器 `~/.dsh/skills/.venv/Scripts/python.exe`）。
成品命名：`对比看板_<YYYY-MM-DD>.html`（单文件，默认输出到 `~/桌面/临时文件` + `pipeline` 留档，两侧 hash 必须一致；可用 `DESKTOP_DIR` 覆盖主输出目录）
版式来源：本地 mac 看板 `/Users/limou/lianban-ladder/lianban-ladder.html`（2026-11-12 对齐）。不要从旧版 Windows
模板拷贝样式；`pipeline/template.html` 已按它重写，改样式后跑 `check.py` + `browser_check.py` 验收。

> 这是用户反复改过口径的页面。UI 细节不是建议，是验收项。
>
> **当前定版（2026-11-12，版式取自本地 mac 看板）**：整页版式对齐 `/Users/limou/lianban-ladder/` 的
> 「今日对照」页——hero 标题 + 5 张统计卡、对照区大标题/七宫格/共同涨停胶囊/吸顶双栏头/居中板数轴、
> 卡片弹窗两栏战绩。内容口径沿用 2026-11-11 配色规则：所有卡片白底；共同股仅用 2px 蓝框 `#356b9a`；
> 概念／历史原因 tag 为橙色（`#ffedd5` / `#c2410c`）；行业琥珀、地域蓝；地域／输赢／终N板行下、
> 概念行上独立显示收盘封单金额／手数；历史共同卡带紫色「终N板」徽标。
> 后续重建必须保留这些规则，不得退回到无 hero、无共同胶囊、无吸顶头的窄版，也不得恢复浅红底、红框或绿色概念 tag。

## 一句话流程

定当前日 → 拉当前涨停池 → 探一个远日期确认源可用 → 拉多年历史池 →
排除当前最高标周期 → 取共同涨停最多且不过大的历史日 → 逐板对齐 →
单文件输出 → Headless Chrome 查溢出/弹窗 → 归档。

## 快速执行

已有缓存、只重建并验收页面：

```powershell
Set-Location "$HOME\.dsh\skills\lianban-duizhao\pipeline"
$PY = "$HOME\.dsh\skills\.venv\Scripts\python.exe"
$env:DESKTOP_DIR = "$HOME\Desktop\临时文件"
$env:CHROME_BIN = "C:\Program Files\Google\Chrome\Application\chrome.exe"
& $PY build.py
& $PY check.py
& $PY browser_check.py
Get-FileHash -Path "对比看板_*.html" -Algorithm SHA256
```

需要更新数据时：

```powershell
Set-Location "$HOME\.dsh\skills\lianban-duizhao\pipeline"
$PY = "$HOME\.dsh\skills\.venv\Scripts\python.exe"
& $PY fetch_kaipan.py            # 开盘啦历史池，可断点续跑
& $PY fetch_current.py           # 东财当前池，校验 qdate
& $PY compare_section.py         # 选择对照日
& $PY fetch_kaipan_detail.py "<对照日>"  # 仅缺详情时执行
& $PY compare_section.py
& $PY fetch_concepts.py          # 概念、行业、地域
& $PY compare_section.py
& $PY build.py
& $PY check.py
& $PY browser_check.py
```

换当前交易日时，先同步改这些硬编码；`build.py` 已从 `section_data.json` 自动读取当前日，无需再改日期：

| 文件 | 变量/文本 |
|---|---|
| `fetch_kaipan.py` | `START`、`END`、`CUR_DATE` |
| `fetch_current.py` | `CUR_DATE` |
| `compare_section.py` | `CUR_DATE`、`MAX_HIS` |

## 数据源选型（关键）

| 源 | 覆盖 | 结论 |
|---|---|---|
| 东方财富 `getTopicZTPool` | 基本只有当前日 | 只用于当前池，不要拿它取历史 |
| 同花顺 `limit_up_pool` | 约近一年 | 旧日期返回 `status_code:-1`、0 只，已弃用为历史源 |
| 开盘啦 `apphis.longhuvip.com` | 2020 年至今日，实测 2020/2022/2023/2024/2026 可用 | **当前采用**；无北交所 |
| Tushare `limit_list_d` | 2020+，字段最全 | 需 token/积分；没有 token 时不要假装能取 |
| BaoStock/日K计算 | 任意年限 | 只有日K，没有首封/封单/原因；仅作兜底，不优先 |

### 先探测，再全量

不要直接循环几年。先拿一个远日期探针：

```python
# 开盘啦：日期带横线，POST 表单，响应可能是 gzip
params = {
    "a": "GetZhangTingTianTi", "c": "FuPanLa", "Date": "2024-03-12",
    "DeviceID": "...", "PhoneOSNew": "2", "VerSion": "5.23.0.1", "apiv": "w44",
}
```

探针必须检查：

- `errcode == "0"`；
- `StockList` 非空；
- 返回的 `Date` 等于请求日期；
- 第一行字段是否还是 `[code, name, lb, timestamp, plate_code, reason, ...]`。

东财旧日期有个坑：HTTP 200、`pool` 为空，但 `qdate` 仍是当前日；**它不会报错，会静默给错数据**。
同花顺旧日期则是 `status_code:-1`。

## 开盘啦接口细节

地址：`https://apphis.longhuvip.com/w1/api/index.php`

公共参数（大多数接口可匿名）：

```text
DeviceID=<uuid>  PhoneOSNew=2  VerSion=5.23.0.1  apiv=w44
User-Agent: Dalvik/2.1.0 ... Android ...
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
Accept-Encoding: gzip
```

### 1）某日涨停梯队（拿成员 + 板数）

```text
a=GetZhangTingTianTi
c=FuPanLa
Date=YYYY-MM-DD
```

`StockList` 每行：

| 下标 | 含义 |
|---|---|
| 0 | 代码 |
| 1 | 名称 |
| 2 | 连板数 |
| 3 | 首封时间戳 |
| 4 | 板块代码 |
| 5 | 当日涨停原因/板块 |
| 9/10 | 市值类字段，别当封单 |

一个交易日一次请求，足够做「共同涨停」和「板数」统计。

### 2）某日某板位详情（拿首封/封单/几天几板）

```text
a=DailyLimitPerformance
c=HisHomeDingPan
Day=YYYY-MM-DD
PidType=1..5      # 1/2/3/4 板，5=5板及以上
Type=4
Index=0
Order=0
st=1000
```

响应是嵌套的：`info = [[row, row, ...], "YYYY-MM-DD"]`，先取 `info[0]` 再遍历。

行字段：

| 下标 | 含义 | 用法 |
|---|---|---|
| 0 | 代码 | 合并 |
| 1 | 名称 | 合并 |
| 4 | 首封时间戳 | 转 `HH:MM` |
| 5 | 当日涨停原因 | **历史标签只用它** |
| 6 | 封单额 | 元；收盘封单金额 |
| 12 | 所属板块 | **会回填当前概念，历史不要用** |
| 18 | 几天几板/连板标签 | `14连板`、`15天13板` |
| 21 | 当日收盘价 | 元；封单手数 = 封单额 ÷ 收盘价 ÷ 100 |

`open_num`（炸板次数）没有可靠字段：历史卡把它设为空，弹窗显示 `—`，
不要用 `[15]` 或 `0` 冒充，否则历史数据会变成假精确。

## 推荐数据结构

`kaipan_history.json`：

```json
{
  "2024-11-05": {
    "total": 171,
    "detail": true,
    "stocks": [
      {
        "code": "603268",
        "name": "松发股份",
        "lb": 14,
        "first_time": 1730784126,
        "reason": "并购重组",
        "high_days": "14连板",
        "order_amount": 33770428,
        "close_price": null,
        "open_num": null
      }
    ]
  }
}
```

- 只对「重叠最多的前 N 个日期」补详情，不要给 1600 天全拉 5 个板位。
- 目标日必须确保 `detail=true`；缺了就 `fetch_kaipan_detail.py <date>`。
- 详情行缺失时保留最小字段，页面用 `reason/industry` 兜底，不要整页报错。
- `close_price` 是当日收盘价（元），`null` 表示源缺价；`compare_section.py` 在 `section_data.json` 的每张卡中
  同时写入 `close_price` 与派生字段 `order_hands`，且 `order_hands = order_amount ÷ close_price ÷ 100`。
  任一输入缺失时 `order_hands = null`，卡片对应位置显示 `—`，不得用其他字段冒充。

`stock_extra.json`（Windows 当前实现，概念 + 行业 + 地域）：

```json
{
  "_date": "2026-11-02",
  "_src": "em",
  "targets": {
    "000525": {
      "industry": "农化制品",
      "region": "江苏",
      "concepts": ["深股通", "草甘膦"]
    }
  }
}
```

- 行业：当前股优先用涨停池 `hybk`，其余用行情接口 `f127`；
- 地域：当前股和历史股都用行情接口 `f128`，例如 `江苏板块` 存为 `江苏`；历史侧展示当前地域分类；
- `profile_of()` 一次请求 `f127,f128`，不要分两个接口重复请求；同日断点续跑要保留并补齐 `region`；
- 退市等股票可能 `f127/f128` 都为空，行业和地域留空即可，不要用概念或涨停原因冒充。

## 核心算法

### 1）当前最高标周期起点

目的：历史对照不能取当前龙头周期内的日期，否则等于拿当前周期和它自己比。

做法：

1. 从当前东财池取最大 `lbc`；
2. 对每只最高标，用腾讯日K从当前日往前数连续涨停；
3. 起点 = 当前日往前 `n-1` 个交易日；
4. 多只最高标取最早起点；
5. 没有日K时，用历史日期列表按交易日偏移兜底；
6. 历史候选只保留 `d < cycle_start`。

示例：新华传媒 11 板，首板 2026-09-21 → 排除 2026-09-21 及之后。

### 2）历史板数

- 开盘啦有 `lb` 就直接用 `lb`，这是源数据，不要用「连续在池天数」重新算；
- 腾讯日K只有近 120 日，不能覆盖 2020–2024；
- 因此 `pool_streak` 要存 `lb`，`board_on()` 在日K没有该日期时回退到源板数；
- 不要把 `pool_streak` 写成 `prev+1`：停牌/缺池会把 8 板算成 2 板，晋级战绩全错。

### 3）选历史对照日

```python
cand = []
for d in dates:
    if d >= CUR_DATE:                 continue
    if cycle_start and d >= cycle_start: continue
    if hist[d]["total"] > MAX_HIS:    continue   # MAX_HIS = 250
    ov = cur_codes & membership[d]
    if ov:
        cand.append((len(ov), d))
cand.sort(reverse=True)               # 重叠优先，并列取最近
n_common, target = cand[0]
```

为什么加 `MAX_HIS`：

- 2024-02-08 有 12 只共同涨停，但当天 505 只涨停；
- 若选它，历史侧 505 张卡，桌面/手机页面都被拉爆；
- 排除单日 >250 只后，2026-10-16 选到 **2024-11-05（171 只，9 只共同，15.3%）**；
- 这个 cap 要写进页脚/README，不能偷偷改规则。

重叠率分母用「当前池里、历史源也覆盖的代码数」，北交所不计：
当前 61 只，开盘啦当前日 59 只，所以分母是 59，不是 61。

### 4）同梯队赢/输

口径：

- 只看同板数、3 板及以上——**这个限定约束的是"交手事件"，不是卡片当前板数**；
  战绩是这只票的属性，每张卡都要算（2026-10-26 踩坑：大千生态当前首板、历史 3 板，
  只给 ≥3 板的卡算导致左右两侧输赢不一致）；
- 次日本股晋级、对手未晋级 = 本股「赢」；
- 对手晋级、本股未晋级 = 本股「输」；
- 停牌日跳过；无日K时用历史源次日板数（次日 lb = 当日 lb+1 判晋级）；
- 统计整个历史池（2020 起），不是只统计目标日。

### 5）共同股的最终高度（终N板）

共同涨停股的历史侧卡片，在输赢小字后标注「终N板」：从历史对照日起，
按历史池逐交易日 lb+1 往后走，断板/缺席即终止，N = 走到的最高连板数
（N 等于当天板数 = 当天就是最后一板）。验证锚点：大千生态 2024-11-07 为 3 板 → 终 13 板。

`next_outcome()` 的常见 bug：

```python
if code in kbars:
    if not has_bar(bars, nxt):
        return "skip"
```

如果日K只有 2026-04 之后，2024 年的 `code in kbars` 仍为真，
就会把所有老日期都判成 skip，战绩全空。正确做法是：

```python
if code in kbars and has_bar(bars, date):
    if not has_bar(bars, nxt):
        return "skip"          # 日K覆盖范围内，次日停牌
    ...                         # 用日K
# 日期不在日K范围 -> 回退到历史源板数
```

## UI / 交互验收项

> 版式基准 = 本地 mac 看板（`/Users/limou/lianban-ladder/lianban-ladder.html`，2026-11-12 对齐）。
> 下面的结构、类名、数量都是验收项，不是风格建议；换样式前先对照这一节。

### 页面版式

- 单文件，无外部 JS/CSS/字体/图片依赖；所有 CSS/JS 内联。
- H1 固定「今日对照」，不要 logo、不要「梯」字图标；浏览器标题 `今日对照 · YYYY-MM-DD`。
- **hero**：H1 + 副标题 `2026年11月11日 · 收盘 · 85 只涨停 · 历史对照`；右侧 5 张统计卡（`.stat`）：
  当前涨停 / 当前晋级 / 最高连板 / 共同涨停 / 重合率。
- **对照区头部**：kicker `历史对照 · 2024-02-19（周一）`；大标题 `共同涨停 21 只  重合率 25.0%`；
  下面一段口径说明（样本数、扫描区间、单日 cap、周期起点、左右只数、点击提示）。
- **聚焦共同票**：按钮 `#cFocusBtn`，点击给 `#view-compare` 加 `.focus`（非共同卡变淡），文案切换为「显示全部」。
- **七宫格**（`.c-stat`）：当前涨停 / 当前晋级 / 当前首板 / 共同涨停 / 历史涨停 / 历史晋级 / 历史首板；
  统计标签固定「当前晋级 / 历史晋级」。
- **共同涨停胶囊**（`.c-chip`）：每只共同股一枚 `名称 当前N板 → 历史N板`，按 max(两侧板数) → 当前板数 → 名称排序；
  数量必须等于共同股数；0 只时给一枚「无共同涨停」占位。
- **吸顶双栏头**（`.c-mhead`，`position:sticky; top:0`）：左「当前 2026-11-11」+ `85 涨停 · 19 晋级 · 66 首板 · 最高 4 板`；
  中间 `VS` 圆标；右「2024-02-19 历史」+ 同样摘要；白底 94% + 模糊，滚动时固定在顶部。
- **对照行**（`.c-row`）：`minmax(0,1fr) 52px minmax(0,1fr)` 三列；中间 `.c-rail` 白底方框显示板数 + 「板」；
  左右 `.c-cell.cur/.his` 内 `.c-cards` 四列。只渲染当前或历史至少一侧有股票的板数行，两侧都无则整行删除；
  无股票一侧用 `.c-none` 占位（`当前最高 4 板` / `历史最高 7 板` / 无则 `—`）。
- 板数行按板数降序；行间用 1px 虚线 `#93c5fd` 分隔、`padding:12px 0`（不再用旧的 28px margin）。
- **页脚**：`.c-note` 一行扫描/口径摘要；`footer` 四段：数据口径、历史对照、周期排除、同梯队战绩 + 免责声明。
- 桌面内容宽度 1240px（比旧版 1440 窄，靠居中留白和 hero/七宫格撑开气势）；背景保留极淡的暖色径向渐变与网格。

### 卡片

- 结构固定四段：`名称 + 行业 tag` → `地域 + 输X + 赢Y + 终N板` → `封单 金额 / 手数` → `概念 tag ×2`。
- 名称 `.name` 15px/750，`flex:0 0 auto`——宁可行业 tag 省略，也不省略名称；行业 `.ind` 琥珀
  （`#fff0d9/#8b5b16`，`.tag.tag-industry`），`flex:0 1 auto; max-width:46%`，可省略。
- 地域 `.region` 蓝（`#e8f1fb/#356b9a`，`.tag.tag-region`）可收缩；输 `.wl.l` 绿 `#1a9e4b`、赢 `.wl.w` 红 `#d43030`，
  都 `flex:none`；有输才写「输X」，有赢才写「赢X」。
- 历史侧共同股在赢/输后追加紫色徽标 `.fin`「终N板」（`#f5f3ff/#6d28d9`，`margin-left:auto; flex:none`），
  其余卡不显示。共同股**不标 ★**，只用 2px 蓝框高亮，背景保持白色。
- 封单行 `.seal` 独立一行：`封单 1.17亿 / 17.9万手`；金额 ≥1亿保留 2 位、≥1万取整；手数 ≥1万保留 1 位；
  缺数据用 `—`，不得编造。手数 = 收盘封单额 ÷ 当日收盘价 ÷ 100（换算约值）。
- 卡片白底、圆角 10px，左缘 3px 侧色条（当前琥珀、历史靛蓝 `.c-cell.cur/.his .c-card`）；
  共同卡 **2px** `#356b9a` 外框 + 极淡蓝光，普通卡 1px `#e8ecf2`；共同卡不改底色、不改三类 tag 配色。
- 概念/历史原因 `.tag.tag-concept` 橙色（`#ffedd5/#c2410c`），单行省略，最多两个。
- 4 列（1440 约 135.5px/卡）、1100 三列、900/768 两列、390 一列；`.c-cards` 必须有 `align-content:start`，
  否则单列时会被对侧行高拉高、页面高度爆炸。
- 标签单行不换行、超长省略；不能把卡片撑破；输赢和「终N板」必须 `flex:none`，不可被挤压隐藏。
- **不显示股票代码、不显示「详情」文字/按钮**；点击整张卡打开弹窗，不要额外链接。
- **标签口径**：当前卡 = 领涨概念前二。首选东财概念板块按当日涨幅反扫
  （`clist/get fs=m:90 t:3 f:!50` 按 `f3` 降序扫成分股，剔除「昨日涨停/昨日连板」等元板块）；
  push2 限流时兜底 = 开盘啦当日详情 `[12]` 前两个（未按涨幅排序，页脚必须注明口径）；
  历史卡 = 当日涨停原因（历史领涨概念无源，不要用当前概念冒充）。
- 行业（东财 `hybk` / 行情接口 `f127`）放股名后；地域（`f128`，去掉「板块」后缀）放输赢前；
  历史股行业/地域用当前分类（行业稳定，不算穿越），源无数据时留空，不要编造。

### 弹窗

- 头部：kicker `当前 · 2026-11-11` / `历史 · 2024-02-19`；标题股票名；右侧板数徽标 `7板` / `首板`；
  标签行依次：地域（蓝，带「地域」小字）、行业（琥珀，带「行业」）、概念（橙）。
- 四项指标固定：首封时间、封单金额、炸板次数、几天几板。
- 状态行 `#m-sub`：`历史日 · 2024-02-19 · 7板 · 汽车零部件 · 上海 · 封单 3.54亿 / 15.3万手`
  （共同历史卡追加「终N板」）。
- 两栏 `.rival-grid`：「赢过对手 N 只 / 输过对手 N 只」，列表每行对手名 + 红底「当前N板」徽章；
  无战绩显示空态；长列表内部滚动（`overflow-y:auto; overflow-x:hidden`），不撑破弹窗。
- 口径脚注写清 3 板+、次日 lb+1、统计范围 2020 起、停牌跳过、历史无炸板。
- 历史源没有炸板次数：显示 `—`；当前卡有 `zbc`：显示 `N 次`；`data-zbc=""` 时 JS 不要 `|| '0'`。
- 几天几板：优先源 `high_days`；1/2 板常为空，兜底 `首板`/`N连板`。
- 打开后焦点放 `.modal-panel`（`tabindex="-1"`），不要自动聚焦关闭按钮（Chrome 会画蓝色 focus 环）；
  支持点遮罩 / × / Esc 关闭；390px 弹窗贴底全宽、不横向溢出。

### 历史标签

开盘啦 `[12] 所属板块` 会回填**当前概念**：2020 年的三五互联会出现「太空光伏」。
所以历史卡**只用当日 `[5] 涨停原因`**。

代价：部分历史卡只有 1 个标签。这是准确性问题，不要为了凑两个标签把当前概念塞回去。
如果用户问起，直接说明「历史卡只用当日原因」。

## 构建后自检

### Python 层

```powershell
Set-Location "$HOME\.dsh\skills\lianban-duizhao\pipeline"
$PY = "$HOME\.dsh\skills\.venv\Scripts\python.exe"
& $PY build.py
& $PY check.py
```

`check.py` 现在校验版式骨架与逐卡内容：

- 对照日早于周期起点、历史日 `detail=true`、`total <= MAX_HIS`；
- `.c-card` 数 = 当前 + 历史；`.c-card.common` = 共同股 × 2；
- hero `.stat` 5 张、七宫格 `.c-stat` 7 格、`.c-chip` = 共同股数（0 只时 1 枚占位）、
  `.c-rail` = 板数层级数；`#cFocusBtn`、`.c-mhead`、`.c-side.cur/.his`、`.c-vs` 必须存在；
- 每张卡：地域/行业/概念 tag 有值才渲染；`.seal` 文本与 `build.seal_text()` 完全一致；
  `order_hands = order_amount ÷ close_price ÷ 100`，任一输入缺失时必须为 `null`；
- 历史共同卡 `.fin` 数量 = 共同股数，且「终N板」文本存在；
- 输/赢小字只在有数据时出现；历史卡 `zbc` 为 `None`（页面空串 → `—`），当前卡非 `None`；
- 页面不出现「详情」、不出现空 tag。

查旧口径残留：

```bash
grep -R "2026-07-03\|同花顺近一年\|2025-10-20" README.md template.html compare_section.py 对比看板_*.html
```

应为空。

### 浏览器层

本机直接运行以下命令即可。脚本自动查找 Chrome（含 mac 的 `Google Chrome.app`），也可用 `CHROME_BIN` 指定；
CDP 必须带 `--remote-allow-origins=*`，只有实际遇到沙箱错误时才设置 `CHROME_NO_SANDBOX=1`：

```powershell
Set-Location "$HOME\.dsh\skills\lianban-duizhao\pipeline"
& "$HOME\.dsh\skills\.venv\Scripts\python.exe" browser_check.py
```

脚本用 `websocket-client` 连 CDP，至少查：

- `document.body.scrollWidth <= innerWidth`（1440 / 390 各一次）；
- `.c-card` 数 = 当前 + 历史；`.c-card.common` = 共同股 × 2；
- `.c-rail` = 板数层级数；`.c-chip` = 共同股数；`.stat` = 5；`.c-stat` = 7；
- `.c-mhead` 计算后 `position === "sticky"`；
- `.c-card .region.tag-region` 数量 = 有地域的卡片数，且地域位于输赢前；
- `.tag-industry` 数量 = 有行业的卡片数；`.tag-concept` = 两侧概念/原因标签总数；
- 三类标签背景色/文字色与配色规则一致；`.c-card` 背景全白；`.c-card.common` 为 **2px** `#356b9a` 蓝框；
- `.tags`、`.seal`、`.c-chip` 均无 `scrollWidth > clientWidth`；
- `.seal` 数量 = 卡片数，且顺序为 `地域行 → 封单行 → 概念行`；
- `.c-card .fin` 数量 = 共同股数；
- 点「聚焦共同票」后 `#view-compare` 带 `.focus`，非共同卡 opacity < 0.5；再点复原；
- 点历史最高板卡：弹窗 `zbc === "—"`、`days` 非空、kicker 以「历史」开头；
- 点当前最高板卡：弹窗 `zbc` 是 `N 次`；390px 弹窗宽度 ≤ 390；
- 页面无 JS 报错（模板里的 `window.__errs` 计数）。

参考基线（2026-11-11 vs 2024-02-19，85 只 / 237 只 / 共同 21 只）：

| 项 | 值 |
|---|---|
| 卡片 | 322（85 + 237） |
| 共同卡 | 42（21 只 × 2 侧） |
| 共同涨停胶囊 | 21 |
| 板数轴 | 5（7 / 4 / 3 / 2 / 首板） |
| 终N板徽标 | 21 |
| 封单行 | 322 |
| 地域 / 行业 / 概念 tag | 315 / 316 / 407 |
| 1440 列数 / 高度 | 4 列 / 约 7200px |
| 1100 / 900 / 768 | 3 / 2 / 2 列 |
| 390 列数 / 高度 | 1 列 / 约 25500px |
| 横向溢出 | 无 |

### 归档

成品统一命名 `对比看板_<YYYY-MM-DD>.html`，输出到 `~/桌面/临时文件` 并在项目目录留档，
两个 hash 必须一致；页面内容变了但归档没变，等于没交付。

## 坑（都踩过）

1. **东财旧日期静默回当前日**：看 `qdate`，不要只看 HTTP 200。
2. **同花顺只有近一年**：老日期 `status_code:-1`，别再试 2024。
3. **开盘啦响应是 gzip**：`b[:2] == b"\x1f\x8b"` 就 `gzip.decompress`，否则 JSON 解析失败。
4. **`DailyLimitPerformance` 不是平铺数组**：`info[0]` 才是行列表。
5. **历史 `[12]` 是当前板块**：会穿越，历史卡只用 `[5]` 原因。
6. **历史没有炸板次数**：填 `—`，不要填 0。
7. **`pool_streak` 不能用连续在池天数**：停牌会把高板算低，必须存源 `lb`。
8. **日K只有近 120 日**：判断 `code in kbars` 前先看 `has_bar(date)`，否则老日期全 skip。
9. **单日 500+ 涨停不要硬上**：加 `MAX_HIS=250`，并在页面/README 说明。
10. **北交所不在开盘啦历史池**：北交所股不参与重合，分母 = 当前池非北交所代码数
    （2026-11-11：1 只北交所，分母 84；2026-10-26：0 只，分母 55）。
11. **当前卡和历史卡标签口径不同**：当前用领涨概念（东财反扫，限流时开盘啦当日 `[12]` 兜底；
    mac 原版用同花顺概念），历史只用当日原因；不要混。行业琥珀 tag 放股名后、地域蓝色 tag 放输赢前、
    概念/原因橙色 tag 放底部，两侧都有；共同股不要再把概念 tag 改成红色。
12. **弹窗 `data-zbc=""`**：JS 用 `zbc === '' ? '—' : ...`，不要 `|| '0'`。
13. **标题/统计标签是用户改过的**：不要恢复 logo、代码、详情、旧标签，也不要把 2026-11-12 的版式
    改回无 hero、无共同胶囊、无吸顶头的窄版。
14. **换日后别改模板里的日期**：`title`、hero 副标题、弹窗脚注都吃 `@@CUR_DATE@@` / `@@DATE_CN@@`，
    扫描区间和周期起点来自 `section_data.json`；只需改 `fetch_kaipan.py` / `fetch_current.py` /
    `compare_section.py` 的日期，再人工更新 README 与本节基线。
15. **Chrome 沙箱**：不加 `--no-sandbox` 会 `sandbox initialization failed`；
    不加 `--remote-allow-origins=*` 会 WebSocket 403。
16. **单文件依赖**：不要引 CDN、外链字体、外部图片；所有 CSS/JS 内联。
17. **开盘啦当天无数据**：当前日的梯队接口返回空 `StockList`、详情接口 `errcode:1020`
    （要等晚间发布，2026-10-26 实测约 19 点后可用）。当前池只能用东财；此时重叠分母
    = 当前池非北交所代码数（2026-10-26 实盘：55 只、0 只北交所、分母 55），
    没法靠开盘啦当前日求交集。
18. **战绩别绑卡片板数**：`if 当前lb>=3 才算战绩` 会让同一只票左右两侧输赢不一致
    （大千生态案例）。所有卡都算，3板+ 只限定历史交手事件。
19. **本机运行环境**：统一使用 `~/.dsh/skills/.venv/Scripts/python.exe`，不要依赖系统 `python` 命令。
    脚本与页面均使用 UTF-8；headless Chrome 残留会占用
    user-data-dir 锁导致 CDP 连不上，重跑前清 `.chrome-cdp*` 目录和残留进程。
20. **东财 `push2` 会限流断连**：连续扫板块成分会 `RemoteDisconnected`，且限流是
    IP 级、按主机族封（push2/push2delay/镜像全封，push2his/push2ex 不在同族不封但也不
    服务 clist），实测持续 2 小时以上。`fetch_concepts.py` 已内置：浏览器 UA + Referer、
    重试退避、单次失败跳过、`stock_extra.json` 按日断点续跑（跨天自动重扫）。
    限流时概念兜底用开盘啦当日详情 `[12]` 前两个（当天=当前概念，可用）；
    F10 核心题材接口（`RPT_F10_CORETHEME_BOARDTYPE`）实测返回空，不可用。
21. **地域/行业可能同时无值**：东财 `f128` 返回如 `江苏板块`，只去掉末尾「板块」；退市等股票
    `f127/f128` 可能都为空（2026-11-02 有 6 只），留空并写入 README，不要编地域或用概念代替。
22. **`align-content:start` 不能丢**：`.c-cards` 默认会给网格轨道均分剩余高度，390px 单列时
    卡片会被对侧上百只股票的行高拉到 190px+，整页从 7200px 涨到 25000px+。改版式后必须检查。
23. **名称优先于行业**：`.name{flex:0 0 auto}`、行业 `flex:0 1 auto; max-width:46%`。若把名称也设成可收缩，
    4 字股名会被行业 tag 挤成「日出东…」。输赢、终N板是 `flex:none`，不能被挤掉。
24. **封单行会溢出**：`封单 5719.9万 / 14.93万手` 在 135px 卡里超 1–3px。格式固定为金额 ≥1万取整、
    手数 ≥1万保留 1 位；322 卡逐卡 `scrollWidth > clientWidth` 必须为 0。
25. **弹窗别自动聚焦关闭按钮**：Chrome 给 `outline:auto` 画一圈蓝环，看起来像蓝色圆按钮。
    打开时 `panel.focus({preventScroll:true})`，并在 `.modal-panel:focus` 上 `outline:none`。

## 当前流水线（Windows 本机版）

项目：`~/.dsh/skills/lianban-duizhao/pipeline/`，截至 2026-11-11 含 2020-01-02 起 1660 个交易日历史池
（历史扫描至 2026-11-10，`kaipan_history.json` 可断点续跑）。流水线：

```powershell
Set-Location "$HOME\.dsh\skills\lianban-duizhao\pipeline"
$PY = "$HOME\.dsh\skills\.venv\Scripts\python.exe"
& $PY fetch_kaipan.py              # 历史池(增量)
& $PY fetch_current.py             # 东财当前池,校验 qdate 防静默回当前日
& $PY compare_section.py           # 首次会提示缺对照日详情
& $PY fetch_kaipan_detail.py "<对照日>"
& $PY compare_section.py           # 生成 section_data.json
& $PY fetch_concepts.py            # 东财领涨概念+行业+地域 -> stock_extra.json,可断点续跑
& $PY compare_section.py
& $PY build.py
& $PY check.py
& $PY browser_check.py
```

换交易日改硬编码：`fetch_kaipan.py` 的 `END`/`CUR_DATE`、`fetch_current.py` 的 `CUR_DATE`、
`compare_section.py` 的 `CUR_DATE`。`build.py` 自动使用 `section_data.json` 中的 `cur_date`。

与 mac 原版的口径差异（本机无对应源，已写进页面页脚）；**版式已于 2026-11-12 对齐 mac 本地看板**，
剩下的差异只在数据源与晋级判定：

- 当前卡标签：领涨概念前二，东财板块反扫优先、开盘啦当日 `[12]` 兜底（无同花顺概念源）；
  行业 tag 用东财 `hybk`（当前股）/ 行情接口 `f127`（历史股），琥珀色，放股名后；
  地域 tag 用行情接口 `f128`，蓝色，去掉「板块」后缀后放在输赢前，历史股同样使用当前地域分类；
  概念/历史原因 tag 统一橙色；三类 tag 的具体色值和 class 以「卡片」验收项为准；
- 晋级战绩判定用开盘啦历史源板数（未接腾讯日K），停牌无法识别；
- 当前池字段映射：首封 `fbt`、封单 `fund`、收盘价 `p ÷ 1000`、炸板 `zbc`、几天几板 `zttj{days,ct}`。

2026-10-26 基线：对照 2024-11-07（190 只，共同 8 只，14.5%），245 卡 / 16 共同卡，
1440/390 无横向溢出，历史最高 11 板弹窗炸板 `—`、当前 4 板弹窗炸板 `N 次`。
当日概念源为开盘啦兜底（push2 限流中），历史股行业待 push2 解封后跑
`fetch_concepts.py` + 重建补齐。

### 2026-11-12 版式定版（整页对齐本地 mac 看板）

- 同一天数据：当前 85 只（最高 4 板，北交所 1 只），对照 **2024-02-19**（237 只，共同 21 只，21/84 = 25.0%），
  周期起点 2026-11-06；322 卡 / 42 共同卡 / 21 枚共同胶囊 / 5 个板数轴（7/4/3/2/首板）/ 21 枚终N板徽标。
- 版式：hero 5 张统计卡（85 / 19 / 4 / 21 / 25.0%）；对照区「共同涨停 21 只 重合率 25.0%」+ 七宫格
  （85 / 19 / 66 / 21 / 237 / 74 / 163）+ 21 枚 `名称 当前N板 → 历史N板` 胶囊 + 吸顶双栏头 + 居中板数轴。
- 卡片仍按 `名称/行业 → 地域/输赢/终N板 → 封单 → 概念/原因` 排列；白底、共同股 2px 蓝框、
  当前侧 3px 琥珀 / 历史侧 3px 靛蓝左缘；`.seal` 322/322，文本逐卡与 `build.seal_text()` 一致。
- 列数实测：1440 4 列 / 1100 3 列 / 900、768 2 列 / 390 1 列；1440 页高约 7200px，
  390 约 25500px，无横向溢出；390 弹窗贴底全宽 390px。
- 地域 315、行业 316、概念 407 个 tag，配色与 2px 蓝框逐卡检查通过；6 只行业、7 只地域无源数据留空。
- 弹窗：kicker + 板数徽标 + 地域/行业/概念标签行 + 四项指标 + 状态行 + 两栏对手；
  历史 7 板炸板 `—`、当前 4 板 `2 次`。
- Python `check.py` + Chrome `browser_check.py` 全部通过（1440/390、聚焦切换、弹窗、无 JS 报错）；
  桌面与项目归档 SHA-256 一致，定版哈希前缀 `6d544611f9eb2779`。

### 2026-11-11 配色定版（封单行 + 白底 + 橙色 tag + 2px 蓝框，版面后被 11-12 取代）

- 当前 85 只（最高 4 板，北交所 1 只），对照 **2024-02-19**（237 只，共同 21 只，重叠 21/84 = 25.0%），
  周期起点 2026-11-06；322 卡 / 42 共同卡，历史最高 7 板。
- 所有卡片白底 `#fff`，共同股仅用 **2px 蓝框** `#356b9a`，普通卡片保持 1px 边框；
  概念／历史原因 tag 统一橙色 `#ffedd5` / `#c2410c`，地域蓝、行业琥珀规则不变。
- 每张卡按 `名称/行业 → 地域/输赢/终N板 → 封单 → 概念/原因` 排列；`.seal` 为独立行，
  322/322 均有收盘封单金额与手数，手数按 `封单额 ÷ 当日收盘价 ÷ 100` 换算。
- 85 只当前股均有东财领涨概念；6 只行业、7 只地域无源数据并留空；历史详情 237/237，
  21 张共同历史卡均有「终N板」。
- Python 逐卡数据自检、1440/390 Chrome 配色、2px 边框、封单行位置与溢出、弹窗检查全部通过；
  桌面与归档 SHA-256 一致，定版哈希前缀 `b2e2daeaa1a1bd1c`。

> 下方 2026-11-11 及更早记录中的窄版布局、红框、浅红底、绿色概念 tag 仅是当时历史快照；
> 当前规则以「2026-11-12 版式定版」+ 上文「UI / 交互验收项」为准。

### 2026-11-02 实盘记录（Windows，地域 + 彩色 tag 已验收）

- 当前 125 只（最高 6 板，北交所 0 只），对照 **2024-02-19**（237 只，共同 25 只，重叠 20.0%），
  周期起点 2026-10-26；362 卡 / 50 共同卡。
- 地域字段取东财 `f128` 并去掉「板块」：当前 125/125、历史 231/237，页面共 356 个地域 tag；
  万方发展、联络互动、龙津药业、亚星客车、精伦电子、国新文化无当前东财资料，地域和行业留空。
- 当前 125 只均有东财领涨概念；历史详情 237/237 完整，25 张共同历史卡都有「终N板」。
- 地域蓝、行业琥珀、概念绿三类 tag 已落地；共同股仅保留红框/底色，不再覆盖概念 tag 颜色；
  名称、行业、地域均可省略，输赢及「终N板」保持可见。
- 1440/390 无横向溢出，356 个地域均在输赢前，概念标签无溢出；历史 7 板炸板 `—`、当前 6 板 `0 次`。
- 桌面与项目归档 SHA-256 一致，彩色 tag 版 hash 前缀 `a50fe6898a938ee0`。

### 2026-10-30 实盘记录（Windows，已验收）

- 当前 47 只（最高 5 板，北交所 0 只），对照 **2026-07-15**（71 只，共同 6 只，重叠 6/47 = 12.8%），
  周期起点 2026-10-26；118 卡 / 12 共同卡；1440/390 无溢出，历史 4 板炸板 `—`、当前 5 板 `3 次`。
- **东财 push2 整族不可用**：`push2`、`push2delay`、`push2his` 全 `RemoteDisconnected`，只有 `push2ex` 活着。
  结果 28 只当前股没有领涨概念 → 标签退回涨停池行业；65/71 只历史股行业留空。
  为此 `compare_section.py` 增加 `tag_src` / `n_tag_fallback`，`build.py` 页脚写明
  「其中 N 只当前股未挂靠到东财概念板块，标签退回涨停池所属行业（非领涨概念）」。
  **不要为了凑标签编数据**：限流恢复后重跑 `fetch_concepts.py` 再重建即可。
- `fetch_concepts.py` 的行业/地域补齐在限流时会卡死：`profile_of()`（原 `industry_of`）每只最多 6 次重试 × 15s，
  100+ 只历史股能搭几小时。判据：`stock_extra.json` 2 分钟不更新就 kill，接受留空并写进 README。
- 开盘啦当日详情 17:20 仍是 `errcode:1020`（实测约 19:00 后发布）。当日概念兜底因此不可用；
  别把 1020 当成功，也别把 `END` 设成当天（空结果会被记进 `kaipan_nodata.json` 永久跳过）。
- 预览图别用 `chrome --screenshot`：相对路径不落地，且写盘是异步的（`Test-Path` 会先返回 False）。
  改用 CDP `Page.captureScreenshot({captureBeyondViewport:true})`，2 分钟内出 1440/390 整页图。
- 候选并列时取最近一天已由 `cand.sort(key=(重叠数, 日期), reverse=True)` 保证（本次 2026-07-15 与
  2024-09-26 同为 6 只，取前者）。

## 一句话验收

> hero 5 卡、七宫格 7 格、共同胶囊数 = 共同股数、吸顶双栏头、居中板数轴和弹窗都在；
> 当前日与历史日都能对上；共同股数量和页面/README 一致；每张卡能开弹窗；
> 当前卡有领涨概念；所有卡片白底、共同股仅 2px 蓝框；地域蓝 tag 在输赢前、行业琥珀 tag 在股名后、概念/历史原因橙 tag 在底部，
> 输赢与「终N板」不被挤压；地域行下独立封单行的金额/手数完整、换算正确且无溢出；无源数据的行业/地域留空；
> 共同股历史卡有「终N板」、无 ★，共同股不改变三类 tag 配色；
> 历史日期早于当前龙头首板；1440/390 无横向溢出；桌面与归档 hash 一致。
