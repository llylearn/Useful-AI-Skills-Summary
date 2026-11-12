# -*- coding: utf-8 -*-
"""
历史组合：今日首板 × 历史同日首板梯队 → 后续 4 板+

用法：
    python3 derive.py                    # 取最近交易日，增量抓数，生成单文件 HTML 到桌面临时文件目录
    python3 derive.py --date 20261030    # 指定日期
    python3 derive.py --no-fetch         # 只用本地缓存
    python3 derive.py --out <dir>        # 指定输出目录（默认 ~/桌面/临时文件）

数据源：
    - 东方财富 getTopicZTPool：当日涨停池（含行业 hybk、封单、炸板、流通市值）
    - 同花顺 limit_up_pool + continuous_limit_up：历史每日涨停池与连板高度（约近一年）
"""
import argparse
import datetime as dt
import glob
import json
import math
import os
import re
import shutil
import time
from bisect import bisect_left
from collections import defaultdict

import requests

from report_html import render_html

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("ZT_DATA_DIR", os.path.join(BASE, "data"))
DEFAULT_OUT = os.path.expanduser(os.environ.get("DESKTOP_DIR", "~/桌面/临时文件"))

EM_URL = ("https://push2ex.eastmoney.com/getTopicZTPool?ut=7eea3edcaed734bea9cbfc24409ed989"
          "&dpt=wz.ztzt&Pageindex=0&pagesize=300&sort=fbt%3Aasc&date={d}")
THS_POOL = ("http://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool?page={p}&limit=200"
            "&field=199112,10,9001,330323,330324,330325,9002,330329,133971,133970,1968584,3475914,9003,9004"
            "&filter=HS,GEM2STAR&order_field=330324&order_type=0&date={d}&_={t}")
THS_LADDER = ("http://data.10jqka.com.cn/dataapi/limit_up/continuous_limit_up"
              "?filter=HS,GEM2STAR&date={d}&_={t}")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": "http://data.10jqka.com.cn/datacenterph/limitup/limtupInfo.html",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# ------------------------------------------------------------------ fetch
def _get_json(url, timeout=20, tries=3):
    for i in range(tries):
        try:
            r = SESSION.get(url, timeout=timeout)
            if r.status_code == 200:
                return json.loads(r.content.decode("utf-8", errors="replace"))
        except Exception:
            pass
        time.sleep(0.6 * (i + 1))
    return None


def fetch_em(date):
    j = _get_json(EM_URL.format(d=date))
    if not j or not j.get("data"):
        return None
    if int(j["data"].get("qdate") or 0) != int(date):
        return None
    return j["data"].get("pool") or []


def fetch_ths(date):
    t = str(int(time.time() * 1000))
    pool, page = [], 1
    while page <= 6:
        j = _get_json(THS_POOL.format(p=page, d=date, t=t))
        if not j or j.get("status_code") != 0:
            break
        d = j.get("data") or {}
        info = d.get("info") or []
        pool.extend(info)
        total = (d.get("page") or {}).get("total") or 0
        if page * 200 >= total or not info:
            break
        page += 1
        time.sleep(0.15)
    if not pool:
        return None
    ladder = _get_json(THS_LADDER.format(d=date, t=t))
    return {"date": date, "pool": pool, "ladder": ladder}


def weekdays(start, end):
    cur = start
    while cur <= end:
        if cur.weekday() < 5:
            yield cur.strftime("%Y%m%d")
        cur += dt.timedelta(days=1)


def ensure_data(target, no_fetch=False, back_days=400):
    os.makedirs(DATA, exist_ok=True)
    em_path = os.path.join(DATA, "em_%s.json" % target)
    day_path = os.path.join(DATA, "day_%s.json" % target)
    if not no_fetch:
        if not os.path.exists(em_path):
            pool = fetch_em(target)
            if pool:
                json.dump({"date": target, "pool": pool}, open(em_path, "w", encoding="utf-8"),
                          ensure_ascii=False)
        if not os.path.exists(day_path):
            day = fetch_ths(target)
            if day:
                json.dump(day, open(day_path, "w", encoding="utf-8"), ensure_ascii=False)
        end = dt.datetime.strptime(target, "%Y%m%d").date()
        start = end - dt.timedelta(days=back_days)
        for d in weekdays(start, end - dt.timedelta(days=1)):
            p = os.path.join(DATA, "day_%s.json" % d)
            if os.path.exists(p):
                continue
            day = fetch_ths(d)
            if day:
                json.dump(day, open(p, "w", encoding="utf-8"), ensure_ascii=False)
            time.sleep(0.2)


# ------------------------------------------------------------------ recs
def hhmm_to_mins(s):
    try:
        v = int(s)
        h, m = v // 10000, (v // 100) % 100
        return h * 60 + m - 570
    except Exception:
        return None


def epoch_to_mins(s):
    try:
        t = dt.datetime.fromtimestamp(int(s))
        return t.hour * 60 + t.minute - 570
    except Exception:
        return None


def parse_hd(hd):
    if hd == "首板":
        return 1
    m = re.match(r"(\d+)天(\d+)板", hd or "")
    if m:
        return int(m.group(2))
    m = re.match(r"(\d+)连板", hd or "")
    if m:
        return int(m.group(1))
    return 1


def rec(date, code, name, height, mins, open_num, turnover, seal, mv, ltype, reason):
    return {"date": date, "code": code, "name": name, "height": int(height), "mins": mins,
            "open_num": open_num or 0, "turnover": turnover or 0.0, "seal": seal or 0.0,
            "mv": mv or 0.0, "ltype": ltype or "", "reason": reason or ""}


def ths_recs(day):
    d = day["date"]
    lad = (day.get("ladder") or {}).get("data") or []
    hmap = {c["code"]: int(t["height"]) for t in lad for c in t["code_list"]}
    out = []
    for x in day.get("pool") or []:
        h = hmap.get(x["code"], 1 if lad else parse_hd(x.get("high_days")))
        out.append(rec(d, x["code"], x["name"], h, epoch_to_mins(x.get("first_limit_up_time")),
                       x.get("open_num"), x.get("turnover_rate"), x.get("order_amount"),
                       x.get("currency_value"), x.get("limit_up_type"), x.get("reason_type")))
    return out


def em_recs(em):
    d = em["date"]
    out = []
    for x in em.get("pool") or []:
        out.append(rec(d, x["c"], x["n"], x.get("lbc") or 1, hhmm_to_mins(x.get("fbt")),
                       x.get("zbc"), x.get("hs"), x.get("fund"), x.get("ltsz"), "", x.get("hybk")))
    return out


# ------------------------------------------------------------------ analyze
def analyze(recs_by_date, dates, target, ind_map, detailed=False):
    N = len(dates)
    idx = {d: i for i, d in enumerate(dates)}

    def prev_date(d):
        i = idx[d]
        return dates[i - 1] if i > 0 else None

    runs, active = [], {}
    for d in dates:
        for r in recs_by_date[d]:
            h, code = r["height"], r["code"]
            a = active.get(code)
            if h == 1:
                run = {"code": code, "name": r["name"], "start": d, "max": 1, "end": d, "known": True}
                runs.append(run)
                active[code] = run
            elif a is not None and a["end"] == prev_date(d) and h == a["max"] + 1:
                a["max"] = h
                a["end"] = d
            else:
                si = idx[d] - (h - 1)
                run = {"code": code, "name": r["name"], "start": dates[si] if si >= 0 else None,
                       "max": h, "end": d, "known": False}
                runs.append(run)
                active[code] = run

    run_by_start = defaultdict(list)
    for r in runs:
        if r["known"]:
            run_by_start[r["start"]].append(r)

    def win(r):
        return r["max"] >= 4

    first_by_date = defaultdict(list)
    for d in dates:
        for r in recs_by_date[d]:
            if r["height"] == 1:
                first_by_date[d].append(r)

    outcome = {}
    for d, lst in first_by_date.items():
        starts = run_by_start.get(d, [])
        for r in lst:
            outcome[(d, r["code"])] = next((x for x in starts if x["code"] == r["code"]), None)

    target_first = first_by_date[target]
    target_codes = {r["code"] for r in target_first}

    cut = max(0, N - 4)
    base_n = base_w = 0
    cohort_days = cohort_hit = 0
    for d in dates[:cut]:
        lst = first_by_date.get(d, [])
        if not lst:
            continue
        cohort_days += 1
        w = 0
        for r in lst:
            base_n += 1
            o = outcome.get((d, r["code"]))
            if o and win(o):
                base_w += 1
                w += 1
        if w:
            cohort_hit += 1

    ov_days = []
    for d in dates:
        if d >= target:
            continue
        S = {r["code"] for r in first_by_date.get(d, [])}
        ov = S & target_codes
        if len(ov) >= 2:
            wins = [x for x in run_by_start.get(d, []) if win(x)]
            ov_days.append({"date": d, "ov": ov, "n_first": len(first_by_date[d]),
                            "wins": wins, "in_ov": any(w["code"] in ov for w in wins)})

    primary = None
    if ov_days:
        primary = max(ov_days, key=lambda x: (x["in_ov"], len(x["ov"]), x["date"]))
    recent = None
    with_wins = [x for x in ov_days if x["wins"]]
    if with_wins:
        recent = max(with_wins, key=lambda x: x["date"])
    no_win = [x for x in ov_days if not x["wins"]]
    counter = max(no_win, key=lambda x: (len(x["ov"]), x["date"])) if no_win else None

    # per-stock memory
    first_idx = defaultdict(list)
    for d in dates:
        for r in first_by_date.get(d, []):
            first_idx[r["code"]].append(idx[d])
    win_idx = defaultdict(list)
    for r in runs:
        if r["known"] and win(r):
            win_idx[r["code"]].append(idx[r["start"]])

    memory = []
    for r in target_first:
        code = r["code"]
        occ = [rr for d in dates for rr in recs_by_date[d]
               if rr["code"] == code and rr["height"] == 1 and d != target]
        self_wins = [x for x in runs if x["code"] == code and x["known"] and win(x)]
        co = {}
        for o in occ:
            if o["date"] == target:
                continue
            for x in run_by_start.get(o["date"], []):
                if win(x) and x["code"] != code:
                    co[(x["name"], x["start"], x["max"])] = 1
        co_names = sorted(co.keys(), key=lambda z: (-z[2], z[1]))
        memory.append({"rec": r, "occ": len(occ), "self": len(self_wins), "co": co_names})
    memory.sort(key=lambda x: (-len(x["co"]), -x["occ"]))

    # model
    n_first_by_date = {d: len(first_by_date.get(d, [])) for d in dates}
    maxh_by_date = {d: max([r["height"] for r in recs_by_date[d]] or [0]) for d in dates}
    feats = ["logmv", "first_hour", "open_num", "log_seal_ratio", "turnover", "yizi",
             "is20", "n_first", "max_height", "prior4", "log_prior1"]

    def fv(r, d):
        i = idx[d]
        return [
            math.log(max(r["mv"], 1e7)),
            (r["mins"] if r["mins"] is not None else 60) / 60.0,
            float(r["open_num"]),
            math.log(max(r["seal"] / max(r["mv"], 1e7) * 1e6, 1e-3)),
            float(r["turnover"]),
            1.0 if "一字" in r["ltype"] else 0.0,
            1.0 if r["code"][:2] in ("30", "68") else 0.0,
            float(n_first_by_date[d]),
            float(maxh_by_date[d]),
            float(bisect_left(win_idx[r["code"]], i)),
            math.log(1 + bisect_left(first_idx[r["code"]], i)),
        ]

    def build(ds):
        X, y = [], []
        for d in ds:
            for r in first_by_date.get(d, []):
                X.append(fv(r, d))
                o = outcome.get((d, r["code"]))
                y.append(1 if (o and win(o)) else 0)
        return X, y

    # 本机 kysec 不允许加载第三方原生库；用纯 Python 实现与旧 NumPy
    # 版本相同的总体标准差、L2 逻辑回归和 sigmoid，避免依赖 .so。
    def design(X, mu, sd):
        return [[1.0] + [(value - mu[j]) / sd[j] for j, value in enumerate(row)]
                for row in X]

    def sigmoid(z):
        z = max(-30.0, min(30.0, z))
        return 1.0 / (1.0 + math.exp(-z))

    def train(X, y):
        n = len(y)
        columns = list(zip(*X))
        mu = [sum(col) / n for col in columns]
        sd = [math.sqrt(sum((value - m) ** 2 for value in col) / n) or 1.0
              for col, m in zip(columns, mu)]
        Xb = design(X, mu, sd)
        xcols = list(zip(*Xb))
        w = [0.0] * len(Xb[0])
        for _ in range(4000):
            p = [sigmoid(sum(value * weight for value, weight in zip(row, w)))
                 for row in Xb]
            errors = [a - b for a, b in zip(p, y)]
            w = [weight - 0.5 * (sum(value * error for value, error in zip(col, errors)) / n
                                 + 1e-3 * weight)
                 for weight, col in zip(w, xcols)]
        return w, mu, sd

    def predict(X, w, mu, sd):
        return [sigmoid(sum(value * weight for value, weight in zip(row, w)))
                for row in design(X, mu, sd)]

    def auc(yy, pp):
        pos = [p for y, p in zip(yy, pp) if y == 1]
        neg = [p for y, p in zip(yy, pp) if y == 0]
        if not pos or not neg:
            return float("nan")
        return sum((a > b) + 0.5 * (a == b) for a in pos for b in neg) / (len(pos) * len(neg))

    model = {"ok": False}
    try:
        tr_end = max(0, cut - 15)
        Xtr, ytr = build(dates[:tr_end])
        Xva, yva = build(dates[tr_end:cut])
        if detailed and len(ytr) > 200 and len(yva) > 30:
            w, mu, sd = train(Xtr, ytr)
            pv = predict(Xva, w, mu, sd)
            Xall, yall = build(dates[:cut])
            w, mu, sd = train(Xall, yall)
            tx = [fv(r, target) for r in target_first]
            tp = predict(tx, w, mu, sd)
            model = {"ok": True, "auc": auc(yva, pv), "base": sum(yall) / len(yall),
                     "coef": dict(zip(feats, w[1:])), "probs": tp}
    except Exception as e:
        model["err"] = str(e)

    return {"dates": dates, "target": target, "runs": runs, "first_by_date": first_by_date,
            "target_first": target_first, "ov_days": ov_days, "primary": primary,
            "recent": recent, "counter": counter, "memory": memory, "model": model,
            "base_n": base_n, "base_w": base_w, "cohort_days": cohort_days,
            "cohort_hit": cohort_hit, "ind_map": ind_map}


# ------------------------------------------------------------------ render
def hhmm(m):
    if m is None:
        return "?"
    return "%02d:%02d" % ((m + 570) // 60, (m + 570) % 60)


def names_of(codes, rmap):
    return "、".join(rmap[c]["name"] for c in codes if c in rmap)


def render_verbose(R):
    d = R["target"]
    dates = R["dates"]
    tf = R["target_first"]
    rmap = {r["code"]: r for r in tf}
    ind = R["ind_map"]
    out = []
    p = out.append

    def F(s):
        return "%s-%s-%s" % (s[:4], s[4:6], s[6:]) if s and len(s) == 8 and s.isdigit() else s

    def order_codes(codes):
        return sorted(codes, key=lambda c: (ind.get(c, "zzz"), rmap.get(c, {}).get("name", "")))

    p("# %s 首板梯队 × 历史同日 4 板+ 复盘" % F(d))
    p("")
    p("> 数据：同花顺涨停池 + 连板梯队，%s ~ %s（%d 个交易日）。" % (F(dates[0]), F(d), len(dates)))
    p("> 今日涨停 %d 只，其中首板 %d 只。" % (len(R.get("all_target", tf)), len(tf)))
    p("> “4 板+”定义：从首板日起连续涨停 ≥ 4 个交易日（含首板当天）。")
    p("")
    p("---")
    p("")

    # summary
    p("## 一、直接结论")
    p("")
    if R["primary"]:
        pr = R["primary"]
        ov_names = names_of(order_codes(pr["ov"]), rmap)
        # largest same-industry subgroup
        groups = defaultdict(list)
        for c in pr["ov"]:
            groups[ind.get(c, "")].append(c)
        groups = {k: v for k, v in groups.items() if k}
        sector, sector_codes = "", []
        if groups:
            sector, sector_codes = max(groups.items(), key=lambda kv: len(kv[1]))
            if len(sector_codes) < 2:
                sector, sector_codes = "", []
        p("1. **组合**：%s（严格按代码重合共 %d 只）。" % (ov_names, len(pr["ov"])))
        if sector:
            p("    - 其中 **%s %d 只**构成板块组合：%s。" % (sector, len(sector_codes), names_of(order_codes(sector_codes), rmap)))
        p("2. **历史同日**：**%s**（当天 %d 只首板）。" % (F(pr["date"]), pr["n_first"]))
        wins_txt = "、".join("%s（%d 板，%s~%s）" % (w["name"], w["max"], F(w["start"]), F(w["end"])) for w in pr["wins"])
        p("3. **该梯队后续 4 板+**：%s。" % (wins_txt or "无"))
        in_ov = [w for w in pr["wins"] if w["code"] in pr["ov"]]
        if in_ov:
            p("    - 其中就在今天组合内的：**%s**。" % "、".join(w["name"] for w in in_ov))
        if R["recent"] and R["recent"]["date"] != pr["date"]:
            rc = R["recent"]
            p("4. **最近一次同组合重演**：**%s**（%d 只重合：%s）→ %s。" % (
                F(rc["date"]), len(rc["ov"]), names_of(order_codes(rc["ov"]), rmap),
                "、".join("%s %d 板" % (w["name"], w["max"]) for w in rc["wins"])))
        if R["counter"]:
            ct = R["counter"]
            p("5. **反例**：%s 重合 %d 只，但该梯队没有走出 4 板+。" % (F(ct["date"]), len(ct["ov"])))
    else:
        p("今天首板股在历史中**没有 ≥2 只同日首板的重合组合**；下面只能做个股“同梯队记忆”与概率排序。")
    p("")

    # ladder
    p("## 二、今日连板天梯（%s）" % F(d))
    p("")
    p("| 高度 | 个股 |")
    p("|---|---|")
    heights = defaultdict(list)
    for r in R.get("all_target", tf):
        heights[r["height"]].append(r["name"])
    for h in sorted(heights, reverse=True):
        label = "首板" if h == 1 else "%d 板" % h
        p("| %s | %s |" % (label, "、".join(sorted(heights[h]))))
    p("")
    p("### 今日首板 %d 只（按行业）" % len(tf))
    p("")
    sec = defaultdict(list)
    for r in tf:
        sec[ind.get(r["code"], "其他")].append(r["name"])
    for k, v in sorted(sec.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        if len(v) >= 2:
            p("- **%s（%d）**：%s" % (k, len(v), "、".join(sorted(v))))
    singles = [n for k, v in sec.items() if len(v) == 1 for n in v]
    if singles:
        p("- **其他（%d）**：%s" % (len(singles), "、".join(sorted(singles))))
    p("")

    # overlap table
    p("## 三、历史同日首板重合 → 后续 4 板+")
    p("")
    p("| 历史日 | 今天首板中当日也首板（重合组合） | 当日首板数 | 该梯队后续 4 板+ | 4 板+在重合内？ |")
    p("|---|---|---|---|---|")
    rows = sorted(R["ov_days"], key=lambda x: (-len(x["ov"]), x["date"]))[:15]
    for x in rows:
        wins = "、".join("%s %d 板" % (w["name"], w["max"]) for w in x["wins"]) or "无"
        flag = "是（%s）" % "、".join(w["name"] for w in x["wins"] if w["code"] in x["ov"]) if x["in_ov"] else "否"
        p("| %s | %s（%d） | %d | %s | %s |" % (F(x["date"]), names_of(order_codes(x["ov"]), rmap), len(x["ov"]),
                                                x["n_first"], wins, flag))
    p("")
    p("> 重合只说明“同一批股票曾同日首板”，不等于必然复制；表中无 4 板+ 的日期同样是有效反例。")
    p("")

    # key case
    p("## 四、关键案例拆解")
    p("")
    for label, x in (("主组合", R["primary"]), ("最近重演", R["recent"])):
        if not x:
            continue
        if label == "最近重演" and R["primary"] and x["date"] == R["primary"]["date"]:
            continue
        p("### %s：%s（重合 %d 只，当日首板 %d 只）" % (label, F(x["date"]), len(x["ov"]), x["n_first"]))
        p("")
        p("- 重合：%s" % names_of(order_codes(x["ov"]), rmap))
        if x["wins"]:
            p("- 4 板+：%s" % "、".join("%s（%d 板，%s~%s）" % (w["name"], w["max"], F(w["start"]), F(w["end"])) for w in x["wins"]))
        else:
            p("- 4 板+：无")
        p("")

    # model
    p("## 五、今日 4 板+ 概率排序（历史统计模型）")
    p("")
    if R["model"].get("ok"):
        m = R["model"]
        p("逻辑回归，特征：流通市值、首封时间、炸板、封单/流通市值、换手、一字、20cm、当日首板数、市场最高板、个股历史 4 板+次数、历史首板次数。")
        p("")
        p("- 验证 AUC = %.3f；全样本基准率 %.2f%%。" % (m["auc"], 100 * m["base"]))
        p("")
        p("| 排名 | 股票 | 概率 | 流通市值 | 首封 | 炸板 | 封单 | 换手 |")
        p("|---|---|---|---|---|---|---|---|")
        order = sorted(range(len(m["probs"])), key=lambda i: -m["probs"][i])
        for k, i in enumerate(order[:10]):
            r = tf[i]
            p("| %d | %s | %.1f%% | %.0f 亿 | %s | %d | %.2f 亿 | %.1f%% |" % (
                k + 1, r["name"], 100 * m["probs"][i], r["mv"] / 1e8, hhmm(r["mins"]),
                r["open_num"], r["seal"] / 1e8, r["turnover"]))
    else:
        p("模型未训练（样本不足）。")
    p("")

    # memory
    p("## 六、个股“同梯队 4 板+”记忆厚度")
    p("")
    p("| 股票 | 历史首板次数 | 自身 4 板+次数 | 同梯队遇到 4 板+只数 |")
    p("|---|---|---|---|")
    for x in R["memory"][:8]:
        p("| %s | %d | %d | %d |" % (x["rec"]["name"], x["occ"], x["self"], len(x["co"])))
    p("")

    # method
    p("## 七、方法与局限")
    p("")
    p("- 首板判定：连板梯队只收录 2 板及以上，不在梯队中的涨停股当前高度按首板处理，避免把“N 天 M 板”误判为 M 板。")
    p("- 4 板+：从首板日起连续涨停 ≥4 个交易日；本窗口基准率 %.2f%%（%d/%d），%.1f%% 的首板梯队日至少出一只 4 板+。" % (
        100.0 * R["base_w"] / max(R["base_n"], 1), R["base_w"], R["base_n"],
        100.0 * R["cohort_hit"] / max(R["cohort_days"], 1)))
    p("- 数据窗口：同花顺历史接口约 1 年；更早年份无法覆盖。")
    p("- 今天之后未知：文中 4 板+ 名字均来自历史同梯队结果，不是对今天这批股票的确定性预测。")
    p("- 本文是数据复盘，不构成投资建议。")
    return "\n".join(out)


def render(R):
    """精简看板：一张表回答组合、历史同日、龙头和最终板数。"""
    d = R["target"]
    dates = R["dates"]
    rmap = {r["code"]: r for r in R["target_first"]}
    ind = R["ind_map"]
    out = []
    p = out.append

    def F(s):
        return "%s-%s-%s" % (s[:4], s[4:6], s[6:]) if s and len(s) == 8 and s.isdigit() else s

    def order_codes(codes):
        return sorted(codes, key=lambda c: (ind.get(c, "zzz"), rmap.get(c, {}).get("name", "")))

    # 所有有历史龙头的重合日均保留；另外保留主组合和最大反例，避免只看好的一面。
    selected = {x["date"]: x for x in R["ov_days"] if x["wins"]}
    for x in (R["primary"], R["recent"], R["counter"]):
        if x:
            selected[x["date"]] = x

    def rank(x):
        if R["primary"] and x["date"] == R["primary"]["date"]:
            return 0
        if R["recent"] and x["date"] == R["recent"]["date"]:
            return 1
        return 2 if x["wins"] else 3

    rows = sorted(selected.values(), key=lambda x: (
        rank(x), -int(x["in_ov"]), -len(x["ov"]), -int(x["date"])))

    p("# %s 当前首板 × 历史龙头" % F(d))
    p("")
    p('<p class="meta">当前首板 %d 只 · 历史窗口 %s ~ %s · %d 条组合记录</p>' % (
        len(R["target_first"]), F(dates[0]), F(d), len(rows)))
    p("")
    p("| 当前首板组合 | 历史共同首板日 | 同梯队历史龙头 | 龙头最高连板 |")
    p("|---|---|---|---|")
    if not rows:
        p("| 近一年暂无符合条件的首板组合 | — | 无 4 板+ | — |")
    for x in rows:
        combo = "%s<br><span class=\"count\">%d 只</span>" % (
            names_of(order_codes(x["ov"]), rmap), len(x["ov"]))
        labels = []
        if R["primary"] and x["date"] == R["primary"]["date"]:
            labels.append('<span class="badge primary">主组合</span>')
        if R["recent"] and x["date"] == R["recent"]["date"]:
            labels.append('<span class="badge recent">最近重演</span>')
        if R["counter"] and x["date"] == R["counter"]["date"] and not x["wins"]:
            labels.append('<span class="badge counter">反例</span>')
        date_cell = F(x["date"]) + (("<br>" + "".join(labels)) if labels else "")
        wins = sorted(x["wins"], key=lambda w: (-w["max"], w["name"]))
        leaders = "<br>".join(
            '%s%s' % (w["name"], '<span class="in">组合内</span>' if w["code"] in x["ov"] else "")
            for w in wins
        ) or '<span class="muted">无 4 板+</span>'
        boards = "<br>".join('<strong>%d 板</strong>' % w["max"] for w in wins) or "—"
        p("| %s | %s | %s | %s |" % (combo, date_cell, leaders, boards))
    p("")
    p("> 仅列有 4 板+ 龙头的历史组合，并保留主组合与反例。板数截至当前交易日；历史结果不是对今天的预测，4 板+ 含首板当天，不构成投资建议。")
    return "\n".join(out)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()
    args.out = os.path.abspath(os.path.expanduser(args.out))

    if args.date:
        target = args.date
    else:
        # 东财 qdate 给出最近交易日
        today = dt.date.today().strftime("%Y%m%d")
        pool = None if args.no_fetch else fetch_em(today)
        target = today if pool else None
        if not target:
            for i in range(1, 15):
                d = (dt.date.today() - dt.timedelta(days=i)).strftime("%Y%m%d")
                if os.path.exists(os.path.join(DATA, "day_%s.json" % d)):
                    target = d
                    break
        if not target:
            raise SystemExit("找不到最近交易日，请用 --date 指定")

    ensure_data(target, args.no_fetch)

    em = None
    em_path = os.path.join(DATA, "em_%s.json" % target)
    if os.path.exists(em_path):
        raw = json.load(open(em_path, encoding="utf-8"))
        if "data" in raw:
            raw = {"date": target, "pool": (raw.get("data") or {}).get("pool") or []}
        raw["date"] = target
        em = raw
    ind_map = {x.get("c"): x.get("hybk") for x in (em or {}).get("pool", []) if x.get("hybk")}

    days = []
    for f in sorted(glob.glob(os.path.join(DATA, "day_*.json"))):
        j = json.load(open(f, encoding="utf-8"))
        if j.get("pool") and j["date"] <= target:
            days.append(j)
    if not days:
        raise SystemExit("没有历史数据")

    recs_by_date = {j["date"]: ths_recs(j) for j in days}
    dates = [j["date"] for j in days]

    if target not in recs_by_date:
        if not em:
            raise SystemExit("目标日既无同花顺池也无东财池：%s" % target)
        recs_by_date[target] = em_recs(em)
        dates.append(target)
        dates.sort()
    elif em:
        # 用东财补齐行业；同花顺已有高度/封板时间则不覆盖
        pass

    R = analyze(recs_by_date, dates, target, ind_map)
    R["all_target"] = recs_by_date[target]

    md = render(R)
    title = "历史组合 · %s-%s-%s" % (target[:4], target[4:6], target[6:])
    html_doc = render_html(md, title)
    os.makedirs(args.out, exist_ok=True)
    fp = os.path.join(args.out, "历史组合_%s.html" % target)
    with open(fp, "w", encoding="utf-8") as f:
        f.write(html_doc)
    # 项目目录留档
    out2 = os.path.join(BASE, "output")
    os.makedirs(out2, exist_ok=True)
    dst = os.path.join(out2, os.path.basename(fp))
    if os.path.abspath(fp) != os.path.abspath(dst):
        shutil.copyfile(fp, dst)
    print(fp)


if __name__ == "__main__":
    main()
