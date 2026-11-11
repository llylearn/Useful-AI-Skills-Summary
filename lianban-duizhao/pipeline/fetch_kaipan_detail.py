# -*- coding: utf-8 -*-
"""开盘啦某日各板位详情 -> 回填 kaipan_history.json[date]
用法: python3 fetch_kaipan_detail.py 2024-11-05
字段(见 SKILL.md):[0]代码 [1]名称 [4]首封时间戳 [5]当日原因 [6]封单额 [12]所属板块(历史勿用) [18]几天几板 [21]收盘价
"""
import requests, json, gzip, uuid, time, sys, datetime as dt
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent
HIST_F = BASE / "kaipan_history.json"

HEADERS = {
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 13; Pixel 6 Build/TQ3A) AppleWebKit/537.36",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Accept-Encoding": "gzip",
}

def call(**kw):
    p = {"DeviceID": str(uuid.uuid4()), "PhoneOSNew": "2",
         "VerSion": "5.23.0.1", "apiv": "w44", **kw}
    r = requests.post("https://apphis.longhuvip.com/w1/api/index.php",
                      data=p, headers=HEADERS, timeout=20)
    b = r.content
    if b[:2] == b"\x1f\x8b":
        b = gzip.decompress(b)
    return json.loads(b.decode("utf-8"))

def hhmm(ts):
    try:
        return dt.datetime.fromtimestamp(int(ts)).strftime("%H:%M")
    except Exception:
        return ""

def fetch_detail(date):
    detail = {}
    for pid in (1, 2, 3, 4, 5):
        j = call(a="DailyLimitPerformance", c="HisHomeDingPan", Day=date,
                 PidType=pid, Type=4, Index=0, Order=0, st=1000)
        if j.get("errcode") not in ("0", 0):
            print(f"  PidType={pid} errcode={j.get('errcode')}")
            continue
        info = j.get("info")
        rows = info[0] if isinstance(info, list) and info else []
        for row in rows:
            if len(row) < 19:
                continue
            detail[str(row[0])] = {
                "first_time": hhmm(row[4]),
                "reason": row[5] or "",
                "order_amount": row[6],
                "close_price": row[21] if len(row) > 21 and row[21] else None,
                "high_days": row[18] or "",
            }
        time.sleep(0.25)
    return detail

def main(date):
    hist = json.loads(HIST_F.read_text("utf-8"))
    if date not in hist:
        raise SystemExit(f"{date} 不在历史池中,先跑 fetch_kaipan.py")
    detail = fetch_detail(date)
    if not detail:
        raise SystemExit(f"{date} 详情为空")
    hit = 0
    for s in hist[date]["stocks"]:
        d = detail.get(s["code"])
        if d:
            s.update(d)
            hit += 1
        else:
            s.setdefault("first_time", "")
            s.setdefault("order_amount", None)
            s.setdefault("high_days", "")
    hist[date]["detail"] = True
    HIST_F.write_text(json.dumps(hist, ensure_ascii=False), "utf-8")
    print(f"{date} 详情回填 {hit}/{len(hist[date]['stocks'])}")

if __name__ == "__main__":
    main(sys.argv[1])
