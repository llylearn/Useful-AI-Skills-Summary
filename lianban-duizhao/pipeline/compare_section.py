# -*- coding: utf-8 -*-
"""选历史对照日 + 同梯队晋级战绩 -> section_data.json
口径(SKILL.md):
- 排除当前最高标周期(当前日往前 n-1 个交易日及之后)
- 单日涨停 > MAX_HIS=250 不做历史对照
- 重叠分母 = 当前池中历史源覆盖的代码数(北交所不计)
- 赢/输:同板数 3 板+,次日本股晋级对手未晋级=赢,反之为输;统计整个历史池
- 次日晋级判定用历史源板数(次日池中 lb == 当日 lb+1)
"""
import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CUR_DATE = "2026-11-11"
MAX_HIS = 250
MIN_BOARD = 3
BASE = Path(__file__).resolve().parent

def is_bj(code):
    return code.startswith(("8", "4", "920"))

def seal_turnover_pct(amount, turnover_amount):
    """封单额/全天成交额百分比；保留原始浮点值，展示时再格式化为两位小数。"""
    try:
        if amount is None or turnover_amount is None:
            return None
        amount, turnover_amount = float(amount), float(turnover_amount)
        if amount < 0 or turnover_amount <= 0:
            return None
        return amount / turnover_amount * 100
    except (TypeError, ValueError, ZeroDivisionError):
        return None

def load():
    hist = json.loads((BASE / "kaipan_history.json").read_text("utf-8"))
    cur = json.loads((BASE / "current_pool.json").read_text("utf-8"))
    return hist, cur

def trading_dates(hist):
    return sorted(hist.keys())

def cycle_start(cur, dates):
    """当前最高标周期起点 = 当前日往前 n-1 个交易日(多只最高标取最早)。"""
    maxlb = max(s["lb"] for s in cur["stocks"])
    starts = []
    for s in cur["stocks"]:
        if s["lb"] == maxlb:
            all_days = dates + [CUR_DATE]
            idx = len(all_days) - 1 - (s["lb"] - 1)
            starts.append(all_days[max(idx, 0)])
    return min(starts), maxlb

def pick_target(hist, cur, dates, cstart):
    cur_codes = {s["code"] for s in cur["stocks"] if not is_bj(s["code"])}
    cand = []
    for d in dates:
        if d >= CUR_DATE or (cstart and d >= cstart):
            continue
        h = hist[d]
        if h["total"] > MAX_HIS:
            continue
        mem = {s["code"] for s in h["stocks"]}
        ov = cur_codes & mem
        if ov:
            cand.append((len(ov), d))
    cand.sort(key=lambda x: (x[0], x[1]), reverse=True)
    n_common, target = cand[0]
    return target, n_common, len(cur_codes), cand[:5]

def build_index(hist, dates):
    """pool[d] = {code: lb}"""
    return {d: {s["code"]: s["lb"] for s in hist[d]["stocks"]} for d in dates}

def final_streak(code, start_date, pool, dates):
    """从 start_date 起逐交易日 lb+1 走到的最终连板数(断板/缺席即终止)。"""
    i = dates.index(start_date)
    lb = pool[start_date].get(code)
    if lb is None:
        return None
    fin = lb
    for j in range(i + 1, len(dates)):
        nlb = pool[dates[j]].get(code)
        if nlb != lb + 1:
            break
        lb = nlb
        fin = nlb
    return fin

def stock_stats(code, hist, dates, pool):
    """该票在整个历史池中 lb>=3 的同梯队赢/输战绩。
    返回 (wins, losses):元素为对手 code。"""
    wins, losses = [], []
    di = {d: i for i, d in enumerate(dates)}
    for d in dates:
        lb = pool[d].get(code)
        if lb is None or lb < MIN_BOARD:
            continue
        i = di[d]
        if i + 1 >= len(dates):
            continue
        nxt = pool[dates[i + 1]]
        self_adv = nxt.get(code) == lb + 1
        for opp, olb in pool[d].items():
            if opp == code or olb != lb:
                continue
            opp_adv = nxt.get(opp) == olb + 1
            if self_adv and not opp_adv:
                wins.append(opp)
            elif opp_adv and not self_adv:
                losses.append(opp)
    return wins, losses

def main():
    hist, cur = load()
    dates = trading_dates(hist)
    cstart, maxlb = cycle_start(cur, dates)
    target, n_common, denom, top5 = pick_target(hist, cur, dates, cstart)
    print(f"周期起点 {cstart}(最高 {maxlb} 板) 对照日 {target} 共同 {n_common}/{denom}")
    print("候选前5:", top5)

    if not hist[target].get("detail"):
        print(f"!! 目标日缺详情,请先跑: python3 fetch_kaipan_detail.py {target}")
        raise SystemExit(2)

    pool = build_index(hist, dates)
    extra_f = BASE / "stock_extra.json"
    extra, concept_src = {}, ""
    if extra_f.exists():
        raw = json.loads(extra_f.read_text("utf-8"))
        extra = raw.get("targets", raw)  # 兼容无 _date 的旧格式
        concept_src = raw.get("_src", "")
    if not extra:
        print("!! 无 stock_extra.json,卡片将没有领涨概念/行业(先跑 fetch_concepts.py)")
    turnover_f = BASE / "turnover_amount.json"
    turnover = {}
    if turnover_f.exists():
        turnover = json.loads(turnover_f.read_text("utf-8")).get("dates", {})
    if not turnover:
        print("!! 无 turnover_amount.json,全天成交额与封成比将留空(先跑 fetch_turnover.py)")
    name_of = {}
    for d in dates:
        for s in hist[d]["stocks"]:
            name_of[s["code"]] = s["name"]
    for s in cur["stocks"]:
        name_of[s["code"]] = s["name"]
    cur_lb = {s["code"]: s["lb"] for s in cur["stocks"]}

    common_codes = {s["code"] for s in cur["stocks"] if not is_bj(s["code"])} & \
                   {s["code"] for s in hist[target]["stocks"]}

    def pack(s, side):
        code = s["code"]
        # 战绩是该票整个历史池的同梯队交手记录,与卡片当前板数无关
        # (stock_stats 内部已限定只统计 lb>=3 的交易日)
        wins, losses = stock_stats(code, hist, dates, pool)
        def opp_names(codes):
            out, seen = [], set()
            for c in codes:
                if c in seen:
                    continue
                seen.add(c)
                nm = name_of.get(c, c)
                if c in cur_lb:
                    nm += f"(当前{cur_lb[c]}板)"
                out.append(nm)
            return out
        ex = extra.get(code) or {}
        card_date = CUR_DATE if side == "cur" else target
        turnover_amount = (turnover.get(card_date) or {}).get(code)
        item = {
            "code": code, "name": s["name"], "lb": s["lb"],
            "common": code in common_codes,
            "wins_n": len(wins), "losses_n": len(losses),
            "wins": opp_names(wins), "losses": opp_names(losses),
            "side": side,
            "industry": ex.get("industry", ""),
            "region": ex.get("region", ""),
            "turnover_amount": turnover_amount,
            "seal_turnover_pct": seal_turnover_pct(s.get("order_amount"), turnover_amount),
        }
        if side == "cur":
            item.update({
                "first_time": s.get("first_time") or "",
                "order_amount": s.get("order_amount"),
                "zbc": s.get("zbc"),
                "high_days": s.get("high_days") or ("首板" if s["lb"] == 1 else f"{s['lb']}连板"),
                # 领涨概念前两个(东财概念板块按当日涨幅排序);无则退回行业
                "tags": (ex.get("concepts") or s.get("tags") or [])[:2],
                # 标注这张卡的标签是不是退回了行业(限流/冷门股),供页脚如实交代口径
                "tag_src": "concept" if ex.get("concepts") else "industry",
            })
        else:
            item.update({
                "first_time": s.get("first_time") or "",
                "order_amount": s.get("order_amount"),
                "zbc": None,   # 历史源没有炸板次数 -> —
                "high_days": s.get("high_days") or ("首板" if s["lb"] == 1 else f"{s['lb']}连板"),
                "tags": [s["reason"]][:1] if s.get("reason") else [],
                # 共同股标注:历史那天起这一波最终走到的连板数
                "final_lb": final_streak(code, target, pool, dates) if code in common_codes else None,
            })
        return item

    cur_cards = [pack(s, "cur") for s in sorted(cur["stocks"], key=lambda x: (-x["lb"], x["code"]))]
    his_cards = [pack(s, "his") for s in sorted(hist[target]["stocks"], key=lambda x: (-x["lb"], x["code"]))]

    out = {
        "cur_date": CUR_DATE, "his_date": target,
        "cur_total": cur["total"], "his_total": hist[target]["total"],
        "n_common": n_common, "denom": denom,
        "rate": round(n_common / denom * 100, 1) if denom else 0,
        "cycle_start": cstart, "max_lb": maxlb,
        "max_board": max(max(s["lb"] for s in cur["stocks"]),
                         max(s["lb"] for s in hist[target]["stocks"])),
        "cur_cards": cur_cards, "his_cards": his_cards,
        "scan": {"start": dates[0], "end": dates[-1], "days": len(dates)},
        "n_bj": sum(1 for s in cur["stocks"] if is_bj(s["code"])),
        "n_tag_fallback": sum(1 for c in cur_cards if c.get("tag_src") == "industry"),
        "max_his": MAX_HIS,
        "concept_src": concept_src,
    }
    (BASE / "section_data.json").write_text(json.dumps(out, ensure_ascii=False), "utf-8")
    print(f"当前 {len(cur_cards)} 卡 / 历史 {len(his_cards)} 卡 / 共同 {n_common} 只 / 重叠率 {out['rate']}%")
    print("meta:", json.dumps({k: out[k] for k in ("his_date", "n_common", "denom", "rate", "cycle_start", "max_lb")}, ensure_ascii=False))

if __name__ == "__main__":
    main()
