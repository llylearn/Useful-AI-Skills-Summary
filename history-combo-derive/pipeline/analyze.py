# -*- coding: utf-8 -*-
import json, glob, os, re, math, csv
from collections import defaultdict, Counter
from bisect import bisect_left
import datetime as dt

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
OUT = []
def p(s=""):
    OUT.append(str(s))

days = []
for f in sorted(glob.glob(os.path.join(DATA, "day_*.json"))):
    j = json.load(open(f, encoding="utf-8"))
    if j.get("pool"):
        days.append(j)
dates = [d["date"] for d in days]
idx = {d: i for i, d in enumerate(dates)}
N = len(dates)

def prev_date(d):
    i = idx[d]
    return dates[i-1] if i > 0 else None

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

recs = []
ladder_missing = 0
for j in days:
    d = j["date"]
    lad = (j.get("ladder") or {}).get("data") or []
    if not lad:
        ladder_missing += 1
    hmap = {}
    for t in lad:
        for c in t["code_list"]:
            hmap[c["code"]] = int(t["height"])
    for x in j["pool"]:
        h = hmap.get(x["code"])
        if h is None:
            # 连板梯队接口只收录2板及以上；不在梯队即当前为首板
            h = 1 if lad else parse_hd(x.get("high_days"))
        mins = None
        try:
            tt = dt.datetime.fromtimestamp(int(x["first_limit_up_time"]))
            mins = tt.hour * 60 + tt.minute - 570
        except Exception:
            pass
        recs.append({
            "date": d, "code": x["code"], "name": x["name"], "height": h,
            "mins": mins, "open_num": x.get("open_num") or 0,
            "turnover": x.get("turnover_rate") or 0.0,
            "seal": x.get("order_amount") or 0.0,
            "mv": x.get("currency_value") or 0.0,
            "ltype": x.get("limit_up_type") or "",
            "reason": x.get("reason_type") or "",
            "chg": x.get("change_rate") or 0.0,
        })

recs_by_date = defaultdict(list)
for r in recs:
    recs_by_date[r["date"]].append(r)

runs = []
active = {}
for d in dates:
    for r in recs_by_date[d]:
        h = r["height"]; code = r["code"]
        a = active.get(code)
        if h == 1:
            run = {"code": code, "name": r["name"], "start": d, "max": 1, "end": d, "known": True}
            runs.append(run); active[code] = run
        elif a is not None and a["end"] == prev_date(d) and h == a["max"] + 1:
            a["max"] = h; a["end"] = d
        else:
            si = idx[d] - (h - 1)
            start = dates[si] if si >= 0 else None
            run = {"code": code, "name": r["name"], "start": start, "max": h, "end": d, "known": False}
            runs.append(run); active[code] = run

run_by_start = defaultdict(list)
for r in runs:
    if r["known"]:
        run_by_start[r["start"]].append(r)

WIN = 4
def is_win(run):
    return run["max"] >= WIN

first_by_date = defaultdict(list)
for r in recs:
    if r["height"] == 1:
        first_by_date[r["date"]].append(r)

outcome = {}
for d, lst in first_by_date.items():
    startruns = run_by_start.get(d, [])
    for r in lst:
        outcome[(d, r["code"])] = next((x for x in startruns if x["code"] == r["code"]), None)

cut = N - 4
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
        if o and is_win(o):
            base_w += 1; w += 1
    if w > 0:
        cohort_hit += 1

p("=== 0. 数据概览 ===")
p("交易日数: %d (%s ~ %s)" % (N, dates[0], dates[-1]))
p("首板样本数(可判定): %d, 其中后续4板+ : %d, 基准率 %.2f%%" % (base_n, base_w, 100.0*base_w/max(base_n,1)))
p("首板梯队日数: %d, 至少1只走出4板+: %d (%.1f%%)" % (cohort_days, cohort_hit, 100.0*cohort_hit/max(cohort_days,1)))
p("梯队数据缺失日数: %d" % ladder_missing)
p("4板+ 启动run数: %d" % len([r for r in runs if r["known"] and is_win(r)]))

today = dates[-1]
today_first = first_by_date.get(today, [])
today_codes = {r["code"] for r in today_first}

def hhmm(m):
    if m is None: return "?"
    return "%02d:%02d" % ((m+570)//60, (m+570)%60)

# today's full ladder
tday = None
for j in days:
    if j["date"] == today:
        tday = j; break
p("")
p("=== 1. 今日 %s 连板天梯 ===" % today)
lad = (tday.get("ladder") or {}).get("data") or []
for t in sorted(lad, key=lambda x: -int(x["height"])):
    p("%s板 (%d只): %s" % (t["height"], t["number"], "、".join(c["name"] for c in t["code_list"])))
p("首板 (%d只): %s" % (len(today_first), "、".join(sorted(r["name"] for r in today_first))))

# sector counts from today_em.csv
sec = {}
try:
    with open(os.path.join(DATA, "today_em.csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row["lbc"] == "1":
                sec.setdefault(row["industry"], []).append(row["name"])
except Exception as e:
    pass
p("")
p("--- 今日首板按行业 ---")
for k, v in sorted(sec.items(), key=lambda x: -len(x[1])):
    if len(v) >= 2:
        p("%s(%d): %s" % (k, len(v), "、".join(v)))

p("")
p("=== 2. 历史同日首板重合 ===")
ov2 = []; ov1 = []
for d in dates:
    if d == today: continue
    S = {r["code"] for r in first_by_date.get(d, [])}
    ov = S & today_codes
    if len(ov) >= 2: ov2.append((d, ov))
    elif len(ov) == 1: ov1.append((d, ov))
if ov2:
    for d, ov in sorted(ov2, key=lambda x: -len(x[1]))[:15]:
        wins = [x for x in run_by_start.get(d, []) if is_win(x)]
        names = "、".join(sorted({r["name"] for r in first_by_date[d] if r["code"] in ov}))
        p("%s 重合%d只: %s | 当日首板%d只 | 4板+: %s" % (d, len(ov), names, len(first_by_date[d]),
            "、".join("%s(%d板)" % (w["name"], w["max"]) for w in wins) or "无"))
else:
    p("无 >=2 只重合的历史日。")
    if ov1:
        p("仅1只重合的历史日 %d 个，最近10个:" % len(ov1))
        for d, ov in ov1[-10:]:
            nm = "、".join(r["name"] for r in first_by_date[d] if r["code"] in ov)
            wins = [x for x in run_by_start.get(d, []) if is_win(x)]
            p("%s %s | 当日4板+: %s" % (d, nm, "、".join(w["name"] for w in wins) or "无"))

# per-stock memory
first_idx_by_code = defaultdict(list)
for d in dates:
    for r in first_by_date.get(d, []):
        first_idx_by_code[r["code"]].append(idx[d])
win_idx_by_code = defaultdict(list)
for r in runs:
    if r["known"] and is_win(r):
        win_idx_by_code[r["code"]].append(idx[r["start"]])

p("")
p("=== 3. 今日个股历史“同梯队4板+”记录 ===")
rows_mem = []
for r in today_first:
    code = r["code"]
    occ = [rr for rr in recs if rr["code"] == code and rr["height"] == 1 and rr["date"] != today]
    self_wins = [x for x in runs if x["code"] == code and x["known"] and is_win(x)]
    co = {}
    for o in occ:
        for x in run_by_start.get(o["date"], []):
            if is_win(x) and x["code"] != code:
                co[(x["name"], x["start"], x["max"])] = 1
    co_names = sorted(co.keys(), key=lambda z: (-z[2], z[1]))
    rows_mem.append((len(co_names), len(occ), len(self_wins), r, co_names))
for cnt, occ_n, sw, r, co_names in sorted(rows_mem, key=lambda x: (-x[0], -x[1])):
    p("%s %s | 历史首板%d次 自身4板+%d次 同梯队遇4板+%d只 | %s" % (
        r["code"], r["name"], occ_n, sw, cnt,
        "、".join("%s(%d板)" % (n, m) for n, d0, m in co_names[:4]) or "-"))

# bucket rates
p("")
p("=== 4. 历史基准率（分桶）===")
def rate(rows):
    if not rows: return "n=0"
    n = len(rows)
    w = sum(1 for r in rows if outcome.get((r["date"], r["code"])) and is_win(outcome[(r["date"], r["code"])]))
    return "n=%d 4板+率=%.2f%%" % (n, 100.0*w/n)
all_first = [r for d in dates[:cut] for r in first_by_date.get(d, [])]
def bm(m):
    if m is None: return "未知"
    if m <= 5: return "09:30-09:35"
    if m <= 30: return "09:35-10:00"
    if m <= 60: return "10:00-10:30"
    if m <= 120: return "10:30-11:30"
    if m <= 180: return "13:00-14:00"
    return "14:00后"
for b in ["09:30-09:35","09:35-10:00","10:00-10:30","10:30-11:30","13:00-14:00","14:00后"]:
    p("首封 %s: %s" % (b, rate([r for r in all_first if bm(r["mins"]) == b])))
def bmv(v):
    v /= 1e8
    if v < 30: return "<30亿"
    if v < 50: return "30-50亿"
    if v < 100: return "50-100亿"
    if v < 300: return "100-300亿"
    return ">300亿"
for b in ["<30亿","30-50亿","50-100亿","100-300亿",">300亿"]:
    p("流通市值 %s: %s" % (b, rate([r for r in all_first if bmv(r["mv"]) == b])))
p("炸板0次: %s" % rate([r for r in all_first if r["open_num"] == 0]))
p("炸板>=1次: %s" % rate([r for r in all_first if r["open_num"] >= 1]))
p("20cm: %s" % rate([r for r in all_first if r["code"][:2] in ("30","68")]))
p("10cm: %s" % rate([r for r in all_first if r["code"][:2] not in ("30","68")]))
p("一字板: %s" % rate([r for r in all_first if "一字" in r["ltype"]]))
p("换手板: %s" % rate([r for r in all_first if "换手" in r["ltype"]]))

# model
nfirst_by_date = {d: len(first_by_date.get(d, [])) for d in dates}
maxh_by_date = {d: max([r["height"] for r in recs_by_date[d]] or [0]) for d in dates}
FN = ["logmv","first_hour","open_num","log_seal_ratio","turnover","yizi","is20","n_first","max_height","prior4","log_prior1"]
def feat(r, d):
    i = idx[d]
    prior4 = bisect_left(win_idx_by_code[r["code"]], i)
    prior1 = bisect_left(first_idx_by_code[r["code"]], i)
    return [
        math.log(max(r["mv"], 1e7)),
        (r["mins"] if r["mins"] is not None else 60) / 60.0,
        float(r["open_num"]),
        math.log(max(r["seal"] / max(r["mv"], 1e7) * 1e6, 1e-3)),
        float(r["turnover"]),
        1.0 if "一字" in r["ltype"] else 0.0,
        1.0 if r["code"][:2] in ("30","68") else 0.0,
        float(nfirst_by_date[d]),
        float(maxh_by_date[d]),
        float(prior4),
        math.log(1 + prior1),
    ]

def build(ds):
    X, y = [], []
    for d in ds:
        for r in first_by_date.get(d, []):
            X.append(feat(r, d))
            o = outcome.get((d, r["code"]))
            y.append(1 if (o and is_win(o)) else 0)
    return X, y

# 与 derive.py 相同的纯 Python 模型，避免本机 kysec 拦截 NumPy 原生库。
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
        pr = [sigmoid(sum(value * weight for value, weight in zip(row, w)))
              for row in Xb]
        errors = [a - b for a, b in zip(pr, y)]
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
    if not pos or not neg: return float("nan")
    return sum((a > b) + 0.5 * (a == b) for a in pos for b in neg) / (len(pos) * len(neg))

def quantile(values, q):
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    low = int(pos)
    high = math.ceil(pos)
    return ordered[low] + (ordered[high] - ordered[low]) * (pos - low)

tr_dates = dates[:cut-15]
va_dates = dates[cut-15:cut]
Xtr, ytr = build(tr_dates); Xva, yva = build(va_dates)
w, mu, sd = train(Xtr, ytr)
pv = predict(Xva, w, mu, sd)
p("")
p("=== 5. 今日4板+候选排序 ===")
p("训练 %d 样本(正例%d) | 验证 %d 样本(正例%d) AUC=%.3f" % (len(ytr), int(sum(ytr)), len(yva), int(sum(yva)), auc(yva, pv)))

Xall, yall = build(dates[:cut])
w, mu, sd = train(Xall, yall)
pal = predict(Xall, w, mu, sd)
p("全样本系数: " + ", ".join("%s=%.2f" % (n, v) for n, v in zip(FN, w[1:])))

today_X = [feat(r, today) for r in today_first]
today_p = predict(today_X, w, mu, sd)
order = sorted(range(len(today_p)), key=lambda i: -today_p[i])
for k, i in enumerate(order):
    r = today_first[i]
    p("%2d. %s %s | 概率%.1f%% | 流通%.0f亿 首封%s 炸%d 封单%.2f亿 换手%.1f%% %s" % (
        k+1, r["code"], r["name"], 100*today_p[i], r["mv"]/1e8, hhmm(r["mins"]),
        r["open_num"], r["seal"]/1e8, r["turnover"], r["ltype"]))

# top decile precision
thr = quantile(pal, 0.9)
sel = [p >= thr for p in pal]
selected_y = [y for y, keep in zip(yall, sel) if keep]
p("历史模型分数前10%%: n=%d, 实际4板+率=%.2f%%" % (
    sum(sel), 100.0 * sum(selected_y) / len(selected_y) if selected_y else 0))

# similar cohorts
p("")
p("=== 6. 相似梯队日（首板数与今日接近、市场高度接近）===")
sim = []
for d in dates[:cut]:
    nf = len(first_by_date.get(d, []))
    if abs(nf - len(today_first)) <= 5 and abs(maxh_by_date[d] - maxh_by_date[today]) <= 1:
        wins = [x for x in run_by_start.get(d, []) if is_win(x)]
        sim.append((d, nf, maxh_by_date[d], wins))
for d, nf, mh, wins in sorted(sim, key=lambda x: x[0])[-12:]:
    p("%s 首板%d 最高%d板 | 4板+: %s" % (d, nf, mh, "、".join("%s(%d板)" % (w["name"], w["max"]) for w in wins) or "无"))

# sector combo history: 白酒
p("")
p("=== 7. 板块首板组合的历史表现 ===")
for kw in ["白酒", "PCB", "覆铜板"]:
    dd = defaultdict(set)
    for r in recs:
        if r["height"] == 1 and kw in r["reason"]:
            dd[r["date"]].add(r["name"])
    days_kw = [(d, v) for d, v in dd.items() if len(v) >= 2]
    p("[%s] 同日>=2只首板的历史日: %d" % (kw, len(days_kw)))
    for d, v in sorted(days_kw)[-5:]:
        wins = [x for x in run_by_start.get(d, []) if is_win(x)]
        p("  %s %d只: %s | 4板+: %s" % (d, len(v), "、".join(sorted(v)), "、".join("%s(%d板)" % (w["name"], w["max"]) for w in wins) or "无"))

open(os.path.join(BASE, "report.txt"), "w", encoding="utf-8").write("\n".join(OUT))
print("report written", len(OUT), "lines")

