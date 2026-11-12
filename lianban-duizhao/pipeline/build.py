# -*- coding: utf-8 -*-
"""组装单文件 HTML -> 桌面临时文件目录 对比看板_<DATE>.html(同时留档项目目录)
用法: python3 build.py

版式: 对齐本地 mac 看板(lianban-ladder)的「今日对照」页面——
hero + 统计卡、对照区大标题/七宫格/共同涨停胶囊、吸顶双栏头、居中板数轴、卡片弹窗。
内容口径不变: 行业/地域/封单行/终N板/橙色概念 tag、共同股 2px 蓝框白底。
"""
import json, html, os, sys, shutil, hashlib
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).resolve().parent
DESKTOP = Path(os.environ.get("DESKTOP_DIR", str(Path.home() / "桌面" / "临时文件"))).expanduser()
WEEK = "一二三四五六日"
SRC_CN = "东财领涨概念"


def esc(s):
    return html.escape(str(s), quote=True)


def fmt_amt(v):
    if v is None or v == "":
        return "—"
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "—"
    if abs(v) >= 1e8:
        return f"{v / 1e8:.2f}亿"
    if abs(v) >= 1e4:
        return f"{v / 1e4:.0f}万"
    return f"{v:.0f}元"


def fmt_hands(v):
    if v is None or v == "":
        return "—"
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "—"
    if abs(v) >= 1e8:
        return f"{v / 1e8:.2f}亿手"
    if abs(v) >= 1e4:
        return f"{v / 1e4:.1f}万手"
    return f"{v:.0f}手"


def seal_text(c):
    amount = fmt_amt(c.get("order_amount"))
    hands = fmt_hands(c.get("order_hands"))
    if amount == "—" and hands == "—":
        return "封单 —"
    return f"封单 {amount} / {hands}"


def board_text(n):
    return "首板" if int(n) <= 1 else f"{n}板"


def card_html(c):
    key = f'{c["side"]}_{c["code"]}'
    cls = "c-card common" if c["common"] else "c-card"
    ind = f'<span class="ind tag tag-industry">{esc(c["industry"])}</span>' if c.get("industry") else ""
    row = ""
    if c.get("region"):
        row += f'<span class="region tag tag-region">{esc(c["region"])}</span>'
    if c["losses_n"]:
        row += f'<span class="wl l" title="同梯队 3 板+，对手晋级而本股未晋级">输{c["losses_n"]}</span>'
    if c["wins_n"]:
        row += f'<span class="wl w" title="同梯队 3 板+，本股晋级而对手未晋级">赢{c["wins_n"]}</span>'
    if c["side"] == "his" and c.get("final_lb"):
        row += (f'<span class="fin" title="自历史日起这一波最终走到的连板数">'
                f'终{c["final_lb"]}板</span>')
    tags = "".join(f'<span class="tag tag-concept">{esc(t)}</span>' for t in c["tags"][:2])
    return (f'<article class="{cls}" data-key="{esc(key)}" data-code="{esc(c["code"])}" '
            f'data-side="{c["side"]}" data-lb="{c["lb"]}" tabindex="0" role="button">'
            f'<div class="card-head"><h3 class="name">{esc(c["name"])}</h3>{ind}</div>'
            f'<div class="c-rg-row">{row}</div>'
            f'<div class="seal">{esc(seal_text(c))}</div>'
            f'<div class="tags">{tags}</div></article>')


def stats_cell(kind, value, label):
    return f'<div class="c-stat {kind}"><b>{value}</b><span>{label}</span></div>'


def build_compare(d):
    cur, his = d["cur_cards"], d["his_cards"]
    cur_max = max(c["lb"] for c in cur)
    his_max = max(c["lb"] for c in his)
    cur_total = len(cur)
    his_total = d["his_total"]
    cur_lianban = sum(1 for c in cur if c["lb"] > 1)
    his_lianban = sum(1 for c in his if c["lb"] > 1)
    cur_first = sum(1 for c in cur if c["lb"] == 1)
    his_first = sum(1 for c in his if c["lb"] == 1)
    n_common = d["n_common"]
    rate = d["rate"]
    wd = WEEK[datetime.strptime(d["his_date"], "%Y-%m-%d").weekday()]

    hero_stats = "".join([
        f'<div class="stat up"><b>{cur_total}</b><span>当前涨停</span></div>',
        f'<div class="stat lb" title="当前日连续涨停 2 天及以上，不含首板"><b>{cur_lianban}</b><span>当前晋级</span></div>',
        f'<div class="stat top"><b>{cur_max}</b><span>最高连板</span></div>',
        f'<div class="stat"><b>{n_common}</b><span>共同涨停</span></div>',
        f'<div class="stat broken"><b>{rate:.1f}%</b><span>重合率</span></div>',
    ])

    stats = "".join([
        stats_cell("cur", cur_total, "当前涨停"),
        stats_cell("cur", cur_lianban, "当前晋级"),
        stats_cell("cur", cur_first, "当前首板"),
        stats_cell("com", n_common, "共同涨停"),
        stats_cell("his", his_total, "历史涨停"),
        stats_cell("his", his_lianban, "历史晋级"),
        stats_cell("his", his_first, "历史首板"),
    ])

    his_by_code = {c["code"]: c for c in his}
    common = [c for c in cur if c["common"] and c["code"] in his_by_code]
    common.sort(key=lambda c: (-max(c["lb"], his_by_code[c["code"]]["lb"]), -c["lb"], c["name"]))
    chips = "".join(
        f'<span class="c-chip" title="{esc(c["name"])} {esc(c["code"])}">'
        f'<b>{esc(c["name"])}</b>'
        f'<i class="cb">{board_text(c["lb"])}</i>'
        f'<em>→</em>'
        f'<i class="hb">{board_text(his_by_code[c["code"]]["lb"])}</i></span>'
        for c in common
    ) or '<span class="c-chip"><b>无共同涨停</b></span>'

    cur_by_lb, his_by_lb = {}, {}
    for c in cur:
        cur_by_lb.setdefault(c["lb"], []).append(c)
    for c in his:
        his_by_lb.setdefault(c["lb"], []).append(c)
    boards = sorted(set(cur_by_lb) | set(his_by_lb), reverse=True)

    rows = []
    for b in boards:
        left = cur_by_lb.get(b, [])
        right = his_by_lb.get(b, [])
        left_none = f"当前最高 {cur_max} 板" if b > cur_max else "—"
        right_none = f"历史最高 {his_max} 板" if b > his_max else "—"
        left_html = ('<div class="c-cards">' + "".join(card_html(c) for c in left) + "</div>"
                     ) if left else f'<div class="c-none">{left_none}</div>'
        right_html = ('<div class="c-cards">' + "".join(card_html(c) for c in right) + "</div>"
                      ) if right else f'<div class="c-none">{right_none}</div>'
        rows.append(f'''
      <div class="c-row" data-board="{b}">
        <div class="c-cell cur">{left_html}</div>
        <div class="c-rail"><b>{b}</b><span>板</span></div>
        <div class="c-cell his">{right_html}</div>
      </div>''')

    sub = (f'以 {d["cur_date"][5:]} 的 {cur_total} 只涨停股为样本，在开盘啦历史涨停池'
           f'（{d["scan"]["start"]} ~ {d["scan"]["end"]}，单日≤{d["max_his"]}只）中逐日比对，'
           f'在当前最高标周期（{d["cycle_start"]} 起）之前取共同涨停最多的一天；'
           f'左右按连板数对齐，含首板（1 板）全量，共 {cur_total} 只 vs {his_total} 只；'
           f'点击任意卡片查看首封、封单和 3 板+ 晋级战绩。')

    note = (f'扫描 {d["scan"]["start"]} ~ {d["scan"]["end"]}（{d["scan"]["days"]} 个交易日）· '
            f'开盘啦历史池 · 并列最多时取最近交易日 · 北交所不参与重合 · '
            f'晋级判定以历史源板数为准（次日 lb = 当日 lb+1）· '
            f'历史对照不取当前最高标首板（{d["cycle_start"]}）及之后 · '
            f'排除单日 &gt;{d["max_his"]} 只的极端普涨日 · 连板家数按 2 板及以上统计（不含首板）· '
            f'首板参与左右对照 · 历史炸板次数不提供')

    return f'''
<section id="view-compare">
  <div class="c-head">
    <div>
      <div class="c-kicker">历史对照 <span>·</span> {d["his_date"]}（周{wd}）</div>
      <h2 class="c-title">共同涨停 <b>{n_common}</b> 只 <span>重合率 {rate:.1f}%</span></h2>
      <p class="c-sub">{sub}</p>
    </div>
    <button class="c-focus" id="cFocusBtn" type="button">聚焦共同票</button>
  </div>

  <div class="c-stats">{stats}</div>

  <div class="c-common">
    <div class="c-common-head"><b>共同涨停</b><span>{n_common} 只</span><em>当前 → 历史</em></div>
    <div class="c-chips">{chips}</div>
  </div>

  <div class="c-mhead">
    <div class="c-side cur">
      <div><span class="c-badge">当前</span><b>{d["cur_date"]}</b></div>
      <i>{cur_total} 涨停 · {cur_lianban} 晋级 · {cur_first} 首板 · 最高 {cur_max} 板</i>
    </div>
    <div class="c-vs">VS</div>
    <div class="c-side his">
      <div><span class="c-badge">历史</span><b>{d["his_date"]}</b></div>
      <i>{his_total} 涨停 · {his_lianban} 晋级 · {his_first} 首板 · 最高 {his_max} 板</i>
    </div>
  </div>

  <div class="c-rows">{"".join(rows)}
  </div>

  <p class="c-note">{note}</p>
</section>''', hero_stats


def build_footer(d):
    date = d["cur_date"]
    y, m, dd = date.split("-")
    date_cn = f"{int(y)}年{int(m)}月{int(dd)}日"
    if d.get("concept_src") == "kpl":
        tag_note = "当前卡标签 = 开盘啦当日所属概念前二（东财 push2 限流，未按涨幅排序）"
    elif d.get("concept_src") == "hybk":
        tag_note = ("当前卡标签 = 东财领涨概念优先；push2 限流且开盘啦当日数据未发布，"
                    "缺概念者退回东财涨停池所属行业（非领涨概念）")
    else:
        tag_note = "当前卡标签 = 东财概念板块按当日涨幅取前二（领涨概念）"
    fallback = ""
    if d.get("n_tag_fallback"):
        fallback = (f'；其中 {d["n_tag_fallback"]} 只当前股未挂靠到东财概念板块，'
                    f'标签退回涨停池所属行业（非领涨概念）')
    return (
        f'<b>数据口径</b>：当前涨停池为东方财富（{date_cn}，共 {d["cur_total"]} 只；'
        f'其中北交所 {d["n_bj"]} 只，开盘啦无北交所数据，不参与重合统计，重叠分母 {d["denom"]}）。'
        f'{tag_note}{fallback}；股名后为所属行业 tag（东财，历史股行业可能因限流留空）；'
        f'输赢前为所属地域 tag（东财 f128，历史股使用当前地域分类，缺失时留空）；'
        f'地域行下为收盘封单金额/手数（手数 = 封单额 ÷ 当日收盘价 ÷ 100，为换算约值，缺数据显示 —）。<br>'
        f'<b>历史对照</b>：开盘啦 apphis.longhuvip.com，扫描区间 {d["scan"]["start"]} ~ {d["scan"]["end"]}'
        f'（共 {d["scan"]["days"]} 个交易日）；历史卡标签只用当日涨停原因'
        f'（开盘啦「所属板块」会回填当前概念，历史不用；当日领涨概念无历史源）。<br>'
        f'<b>周期排除</b>：当前最高标 {d["max_lb"]} 板，首板日 {d["cycle_start"]}，该日及之后不参与历史对照；'
        f'单日涨停 &gt; {d["max_his"]} 只的日期不做对照（MAX_HIS={d["max_his"]}）。<br>'
        f'<b>同梯队战绩</b>：同板数 3 板及以上，次日晋级胜出计「赢」、对手晋级计「输」，'
        f'统计范围为整个历史池（2020 起），晋级判定以历史源板数为准（次日 lb = 当日 lb+1）。'
        f'历史源无炸板次数，显示 —。<br>'
        f'本页仅为公开数据整理，不构成任何投资建议，据此操作风险自担。'
    )


def main():
    d = json.loads((BASE / "section_data.json").read_text("utf-8"))
    DATE = d["cur_date"]
    year, month, day = DATE.split("-")
    DATE_CN = f"{int(year)}年{int(month)}月{int(day)}日"
    tpl = (BASE / "template.html").read_text("utf-8")

    compare, hero_stats = build_compare(d)

    detail = {}
    for c in d["cur_cards"] + d["his_cards"]:
        detail[f'{c["side"]}_{c["code"]}'] = {
            "name": c["name"], "lb": c["lb"], "side": c["side"],
            "date": DATE if c["side"] == "cur" else d["his_date"],
            "common": c["common"],
            "industry": c.get("industry", ""),
            "region": c.get("region", ""),
            "first_time": c["first_time"], "order_amount": c["order_amount"],
            "close_price": c.get("close_price"), "order_hands": c.get("order_hands"),
            "zbc": "" if c["zbc"] is None else c["zbc"],
            "high_days": c["high_days"], "tags": c["tags"],
            "final_lb": c.get("final_lb"),
            "wins": c["wins"], "losses": c["losses"],
            "seal": seal_text(c),
        }

    html_out = tpl
    for k, v in {
        "@@CUR_DATE@@": DATE,
        "@@DATE_CN@@": DATE_CN,
        "@@CUR_TOTAL@@": str(d["cur_total"]),
        "@@HERO_STATS@@": hero_stats,
        "@@COMPARE@@": compare,
        "@@FOOTER@@": build_footer(d),
        "@@DETAIL@@": json.dumps(detail, ensure_ascii=False).replace("</", "<\\/"),
    }.items():
        html_out = html_out.replace(k, v)

    local = BASE / f"对比看板_{DATE}.html"
    local.write_text(html_out, "utf-8")
    DESKTOP.mkdir(parents=True, exist_ok=True)
    dest = DESKTOP / f"对比看板_{DATE}.html"
    shutil.copy(local, dest)
    h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    print(f"输出 {local}  {h(local)}")
    print(f"主输出 {dest}  {h(dest)}")
    assert h(local) == h(dest), "归档 hash 不一致"
    print("hash 一致 ✓")


if __name__ == "__main__":
    main()
