# -*- coding: utf-8 -*-
"""开盘啦历史涨停池 -> kaipan_history.json，可断点续跑。
无数据的 weekday(节假日) 记入 kaipan_nodata.json，重跑不会重复请求。
"""
import requests, json, gzip, uuid, time, sys, datetime as dt
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

START = "2020-01-01"
END = "2026-11-10"          # 当前日(2026-11-11)扫到前一交易日
CUR_DATE = "2026-11-11"

BASE = Path(__file__).resolve().parent
HIST_F = BASE / "kaipan_history.json"
NODATA_F = BASE / "kaipan_nodata.json"

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

def fetch_day(d):
    """返回 stocks 列表;非交易日/无数据返回 None。"""
    j = call(a="GetZhangTingTianTi", c="FuPanLa", Date=d)
    if j.get("errcode") != "0" and j.get("errcode") != 0:
        return None
    sl = j.get("StockList") or []
    if not sl:
        return None
    stocks = []
    for row in sl:
        if len(row) < 6:
            continue
        stocks.append({
            "code": str(row[0]), "name": row[1], "lb": int(row[2]),
            "reason": row[5] or "",
        })
    return stocks

def main():
    hist = json.loads(HIST_F.read_text("utf-8")) if HIST_F.exists() else {}
    nodata = set(json.loads(NODATA_F.read_text("utf-8"))) if NODATA_F.exists() else set()

    d0 = dt.date.fromisoformat(START)
    d1 = dt.date.fromisoformat(END)
    days = []
    d = d0
    while d <= d1:
        if d.weekday() < 5:
            days.append(d.isoformat())
        d += dt.timedelta(days=1)

    todo = [d for d in days if d not in hist and d not in nodata]
    print(f"weekday 总数 {len(days)},已有 {len(hist)},无数据 {len(nodata)},待抓 {len(todo)}")

    done = 0
    for i, d in enumerate(todo):
        for attempt in range(3):
            try:
                stocks = fetch_day(d)
                break
            except Exception as e:
                print(f"  {d} 第{attempt+1}次失败: {e}")
                time.sleep(2 * (attempt + 1))
                stocks = "FAIL"
        if stocks == "FAIL":
            print(f"  {d} 跳过(3次失败)")
            continue
        if stocks is None:
            nodata.add(d)
        else:
            hist[d] = {"total": len(stocks), "detail": False, "stocks": stocks}
            done += 1
        if (i + 1) % 20 == 0 or i == len(todo) - 1:
            HIST_F.write_text(json.dumps(hist, ensure_ascii=False), "utf-8")
            NODATA_F.write_text(json.dumps(sorted(nodata)), "utf-8")
            print(f"进度 {i+1}/{len(todo)}  有效 {len(hist)}  无数据 {len(nodata)}")
        time.sleep(0.25)

    HIST_F.write_text(json.dumps(hist, ensure_ascii=False), "utf-8")
    NODATA_F.write_text(json.dumps(sorted(nodata)), "utf-8")
    print(f"完成:有效交易日 {len(hist)},无数据 {len(nodata)},本轮新增 {done}")

if __name__ == "__main__":
    main()
