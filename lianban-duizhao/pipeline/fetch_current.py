# -*- coding: utf-8 -*-
"""东财当前涨停池 -> current_pool.json
字段:c代码 n名称 lbc连板数 fbt首封(HHMMSS) fund封单额(元) p收盘价(原始值/1000) zbc炸板次数 hybk行业 zttj{days,ct}
"""
import requests, json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CUR_DATE = "2026-11-11"
BASE = Path(__file__).resolve().parent

def is_bj(code):
    return code.startswith(("8", "4", "920"))

def fmt_fbt(v):
    s = f"{int(v):06d}"
    return f"{s[:2]}:{s[2:4]}"

def high_days_text(lb, days, ct):
    if lb <= 1:
        return "首板"
    if days == ct:
        return f"{ct}连板"
    return f"{days}天{ct}板"

def main():
    date_arg = CUR_DATE.replace("-", "")
    url = "https://push2ex.eastmoney.com/getTopicZTPool"
    params = {"ut": "7eea3edcaed734bea9cbfc24409ed989", "dpt": "wz.ztzt",
              "Pageindex": 0, "pagesize": 500, "sort": "fbt:asc", "date": date_arg}
    r = requests.get(url, params=params, timeout=20)
    j = r.json()
    data = j.get("data") or {}
    qdate = str(data.get("qdate") or "")
    if qdate != date_arg:
        raise SystemExit(f"qdate={qdate} != 请求日 {date_arg},当天可能非交易日或数据未出")
    pool = data.get("pool") or []
    stocks = []
    for p in pool:
        lb = int(p.get("lbc") or 1)
        zt = p.get("zttj") or {}
        stocks.append({
            "code": p["c"], "name": p["n"], "lb": lb,
            "first_time": fmt_fbt(p.get("fbt") or 0),
            "order_amount": p.get("fund"),
            "close_price": (p.get("p") / 1000 if p.get("p") else None),
            "zbc": p.get("zbc"),
            "tags": [t for t in [p.get("hybk")] if t][:2],
            "high_days": high_days_text(lb, zt.get("days", lb), zt.get("ct", lb)),
            "bj": is_bj(p["c"]),
        })
    out = {"date": CUR_DATE, "total": len(stocks), "stocks": stocks}
    (BASE / "current_pool.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8")
    n_bj = sum(1 for s in stocks if s["bj"])
    print(f"当前池 {len(stocks)} 只(北交所 {n_bj} 只),最高 {max(s['lb'] for s in stocks)} 板")

if __name__ == "__main__":
    main()
