# -*- coding: utf-8 -*-
import requests, json, time, os, datetime, sys

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
os.makedirs(DATA, exist_ok=True)

H = {
    "Referer": "http://data.10jqka.com.cn/datacenterph/limitup/limtupInfo.html",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
}
FIELDS = "199112,10,9001,330323,330324,330325,9002,330329,133971,133970,1968584,3475914,9003,9004"
POOL = ("http://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool?page={p}&limit=200&field=" + FIELDS +
        "&filter=HS,GEM2STAR&order_field=330324&order_type=0&date={d}&_={t}")
LADDER = "http://data.10jqka.com.cn/dataapi/limit_up/continuous_limit_up?filter=HS,GEM2STAR&date={d}&_={t}"

s = requests.Session()
s.headers.update(H)

def get(url, tries=3):
    for i in range(tries):
        try:
            r = s.get(url, timeout=20)
            if r.status_code == 200:
                return json.loads(r.content.decode("utf-8", errors="replace"))
        except Exception as e:
            pass
        time.sleep(0.6 * (i + 1))
    return None

def fetch_day(d):
    t = str(int(time.time() * 1000))
    pool, page = [], 1
    while page <= 6:
        j = get(POOL.format(p=page, d=d, t=t))
        if not j or j.get("status_code") != 0:
            break
        dd = j.get("data") or {}
        info = dd.get("info") or []
        pool.extend(info)
        total = (dd.get("page") or {}).get("total") or 0
        if page * 200 >= total or not info:
            break
        page += 1
        time.sleep(0.15)
    lad = get(LADDER.format(d=d, t=t))
    return pool, lad

def main():
    start = datetime.date(2025, 9, 1)
    end = datetime.date(2026, 10, 30)
    dates = []
    cur = start
    while cur <= end:
        if cur.weekday() < 5:
            dates.append(cur.strftime("%Y%m%d"))
        cur += datetime.timedelta(days=1)
    log = open(os.path.join(BASE, "fetch_log.txt"), "w", encoding="utf-8")
    ok = 0
    for i, d in enumerate(dates):
        fp = os.path.join(DATA, "day_%s.json" % d)
        if os.path.exists(fp):
            ok += 1
            continue
        pool, lad = fetch_day(d)
        if pool:
            with open(fp, "w", encoding="utf-8") as f:
                json.dump({"date": d, "pool": pool, "ladder": lad}, f, ensure_ascii=False)
            ok += 1
            log.write("%s ok pool=%d\n" % (d, len(pool)))
        else:
            log.write("%s empty\n" % d)
        log.flush()
        if i % 20 == 0:
            print("progress %d/%d ok=%d %s" % (i, len(dates), ok, d), flush=True)
        time.sleep(0.2)
    log.write("DONE ok=%d total=%d\n" % (ok, len(dates)))
    log.close()
    print("DONE ok=%d/%d" % (ok, len(dates)))

if __name__ == "__main__":
    main()
