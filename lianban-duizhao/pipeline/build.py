# -*- coding: utf-8 -*-
"""组装单文件 HTML -> 桌面临时文件目录 对比看板_<DATE>.html(同时留档项目目录)
用法: python3 build.py
"""
import json, html, os, sys, shutil, hashlib
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).resolve().parent
DESKTOP = Path(os.environ.get("DESKTOP_DIR", str(Path.home() / "桌面" / "临时文件"))).expanduser()

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
        return f"{v / 1e4:.1f}万"
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
        return f"{v / 1e4:.2f}万手"
    return f"{v:.0f}手"

def seal_text(c):
    amount = fmt_amt(c.get("order_amount"))
    hands = fmt_hands(c.get("order_hands"))
    if amount == "—" and hands == "—":
        return "封单 —"
    return f"封单 {amount} / {hands}"

def card_html(c):
    key = f'{c["side"]}_{c["code"]}'
    cls = "c-card common" if c["common"] else "c-card"
    wl = f'<span class="region tag tag-region">{esc(c["region"])}</span>' if c.get("region") else ""
    if c["losses_n"]:
        wl += f'<span class="l">输{c["losses_n"]}</span>'
    if c["wins_n"]:
        wl += f'<span class="w">赢{c["wins_n"]}</span>'
    if c["side"] == "his" and c.get("final_lb"):
        wl += f'<span class="fin">终{c["final_lb"]}板</span>'
    tags = "".join(f'<span class="tag tag-concept">{esc(t)}</span>' for t in c["tags"][:2])
    ind = f'<span class="ind tag tag-industry">{esc(c["industry"])}</span>' if c.get("industry") else ""
    seal = esc(seal_text(c))
    return (f'<div class="{cls}" data-key="{esc(key)}">'
            f'<div class="nm"><span class="stock-name">{esc(c["name"])}</span>{ind}</div>'
            f'<div class="wl">{wl}</div>'
            f'<div class="seal">{seal}</div>'
            f'<div class="tags">{tags}</div></div>')

def build_rows(d):
    cur_by, his_by = {}, {}
    for c in d["cur_cards"]:
        cur_by.setdefault(c["lb"], []).append(c)
    for c in d["his_cards"]:
        his_by.setdefault(c["lb"], []).append(c)
    out = []
    for lb in sorted(set(cur_by) | set(his_by), reverse=True):
        left = "".join(card_html(c) for c in cur_by.get(lb, [])) or '<div class="empty">—</div>'
        right = "".join(card_html(c) for c in his_by.get(lb, [])) or '<div class="empty">—</div>'
        label = "首板" if lb == 1 else f"{lb}板"
        out.append(f'<div class="row"><div class="cards">{left}</div>'
                   f'<div class="axis"><span>{label}</span></div>'
                   f'<div class="cards">{right}</div></div>')
    return "\n".join(out)

def main():
    d = json.loads((BASE / "section_data.json").read_text("utf-8"))
    DATE = d["cur_date"]
    year, month, day = DATE.split("-")
    DATE_CN = f"{int(year)}年{int(month)}月{int(day)}日"
    tpl = (BASE / "template.html").read_text("utf-8")

    detail = {}
    for c in d["cur_cards"] + d["his_cards"]:
        detail[f'{c["side"]}_{c["code"]}'] = {
            "name": c["name"], "lb": c["lb"], "side": c["side"],
            "industry": c.get("industry", ""),
            "first_time": c["first_time"], "order_amount": c["order_amount"],
            "close_price": c.get("close_price"), "order_hands": c.get("order_hands"),
            "zbc": "" if c["zbc"] is None else c["zbc"],
            "high_days": c["high_days"], "tags": c["tags"],
            "wins": c["wins"], "losses": c["losses"],
        }

    if d.get("concept_src") == "kpl":
        tag_note = "当前卡标签 = 开盘啦当日所属概念前二(东财 push2 限流,未按涨幅排序)"
    elif d.get("concept_src") == "hybk":
        tag_note = "当前卡标签 = 东财领涨概念优先;push2 限流且开盘啦当日数据未发布,缺概念者退回东财涨停池所属行业(非领涨概念)"
    else:
        tag_note = "当前卡标签 = 东财概念板块按当日涨幅取前二(领涨概念)"
    fallback_note = ""
    if d.get("n_tag_fallback"):
        fallback_note = (f';其中 {d["n_tag_fallback"]} 只当前股未挂靠到东财概念板块,'
                         f'标签退回涨停池所属行业(非领涨概念)')
    footer = (
        f'当前涨停池:东方财富({DATE_CN},共 {d["cur_total"]} 只;其中北交所 {d["n_bj"]} 只,开盘啦无北交所数据,不参与重合统计,重叠分母 {d["denom"]})。'
        f'{tag_note}{fallback_note};股名后为所属行业 tag(东财,历史股行业可能因限流留空),'
        f'输赢前为所属地域 tag(东财 f128,历史股使用当前地域分类,缺失时留空);'
        f'地域行下为收盘封单金额/手数(手数 = 封单额 ÷ 当日收盘价 ÷ 100,为换算约值,缺数据显示 —)。<br>'
        f'历史源:开盘啦 apphis.longhuvip.com,扫描区间 {d["scan"]["start"]} ~ {d["scan"]["end"]}(共 {d["scan"]["days"]} 个交易日)。'
        f'历史卡标签只用当日涨停原因(开盘啦「所属板块」会回填当前概念,历史不用;当日领涨概念无历史源)。<br>'
        f'周期排除:当前最高标 {d["max_lb"]} 板,首板日 {d["cycle_start"]},该日及之后不参与历史对照;'
        f'单日涨停 &gt; {d["max_his"]} 只的日期不做对照(MAX_HIS={d["max_his"]})。<br>'
        f'同梯队战绩:同板数 3 板及以上,次日晋级胜出计「赢」、对手晋级计「输」,统计范围为整个历史池(2020 起),'
        f'晋级判定以历史源板数为准(次日 lb = 当日 lb+1)。历史源无炸板次数,显示 —。'
    )

    html_out = tpl
    for k, v in {
        "@@CUR_DATE@@": DATE,
        "@@HIS_DATE@@": d["his_date"],
        "@@N_COMMON@@": str(d["n_common"]),
        "@@RATE@@": str(d["rate"]),
        "@@CUR_TOTAL@@": str(d["cur_total"]),
        "@@HIS_TOTAL@@": str(d["his_total"]),
        "@@ROWS@@": build_rows(d),
        "@@FOOTER@@": footer,
        "@@DETAIL@@": json.dumps(detail, ensure_ascii=False),
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
