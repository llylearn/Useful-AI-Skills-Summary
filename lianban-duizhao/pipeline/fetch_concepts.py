# -*- coding: utf-8 -*-
"""个股领涨概念 + 行业 + 地域 -> stock_extra.json
概念(仅当前侧卡片需要;历史卡标签固定用当日涨停原因):
  首选东财概念板块按当日涨幅反扫(clist,剔除「昨日涨停」等元板块)——真·领涨;
  push2 限流时兜底:开盘啦当日 DailyLimitPerformance 的 [12] 所属板块前两个
  (该字段当天=当前概念,可用;历史日不可用,会穿越)。
行业:当前股用东财涨停池 hybk,历史股用行情接口 f127(行业分类稳定,不构成穿越)。
地域:当前股和历史股均用行情接口 f128,去掉「板块」后缀后显示在输赢前。
依赖 section_data.json(先跑 compare_section.py)。同一天可断点续跑,跨天自动重扫。
输出 {"_date":..., "_src":"em"|"kpl", "targets":{code:{industry,region,concepts}}}
"""
import requests, json, re, sys, time, gzip, uuid
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent
META = re.compile(r"昨日|涨停|连板|多板|破净|百元")
EXTRA_F = BASE / "stock_extra.json"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
})

KPL_H = {
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 13; Pixel 6 Build/TQ3A) AppleWebKit/537.36",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Accept-Encoding": "gzip",
}

def _get(url, params, tries=6):
    """失败重试退避;仍失败返回 None(调用方跳过,不中断整轮扫描)。"""
    for i in range(tries):
        try:
            return SESSION.get(url, params=params, timeout=15)
        except requests.RequestException:
            time.sleep(2 * (i + 1))
    return None

def clist(**kw):
    p = {"pn": 1, "pz": 100, "po": 1, "np": 1, "fltt": 2, "invt": 2,
         "fid": "f3", **kw}
    r = _get("https://push2.eastmoney.com/api/qt/clist/get", p)
    if r is None:
        return []
    return (r.json().get("data") or {}).get("diff") or []

def push2_alive():
    r = _get("https://push2.eastmoney.com/api/qt/clist/get",
             {"pn": 1, "pz": 1, "fs": "m:90 t:3", "fields": "f12"}, tries=2)
    return r is not None and r.status_code == 200

def kpl_call(**kw):
    p = {"DeviceID": str(uuid.uuid4()), "PhoneOSNew": "2",
         "VerSion": "5.23.0.1", "apiv": "w44", **kw}
    r = requests.post("https://apphis.longhuvip.com/w1/api/index.php",
                      data=p, headers=KPL_H, timeout=15)
    b = r.content
    if b[:2] == b"\x1f\x8b":
        b = gzip.decompress(b)
    return json.loads(b.decode("utf-8"))

def concepts_from_kaipanla(date, codes):
    """开盘啦当日详情 [12] 所属板块前两个。返回 {code: [概念,...]}。"""
    out = {}
    for pid in (1, 2, 3, 4, 5):
        j = kpl_call(a="DailyLimitPerformance", c="HisHomeDingPan", Day=date,
                     PidType=pid, Type=4, Index=0, Order=0, st=1000)
        if j.get("errcode") not in ("0", 0):
            continue
        info = j.get("info")
        rows = info[0] if isinstance(info, list) and info else []
        for row in rows:
            if len(row) > 12 and str(row[0]) in codes and row[12]:
                out[str(row[0])] = [t for t in str(row[12]).split("、") if t][:2]
        time.sleep(0.3)
    return out

def all_concept_boards():
    """按涨幅降序的全部概念板块(过滤元板块)。"""
    boards, pn = [], 1
    while True:
        diff = clist(pn=pn, fs="m:90 t:3 f:!50", fields="f12,f14,f3")
        if not diff:
            break
        boards += [b for b in diff if not META.search(b["f14"])]
        if len(diff) < 100:
            break
        pn += 1
        time.sleep(0.25)
    return boards

def profile_of(code):
    """一次请求同时补行业 f127 和地域 f128;地域去掉展示冗余的「板块」。"""
    secid = ("1." if code[0] in "69" else "0.") + code
    r = _get("https://push2.eastmoney.com/api/qt/stock/get",
             {"secid": secid, "fields": "f57,f58,f127,f128"})
    if r is None:
        return {"industry": "", "region": ""}
    data = r.json().get("data") or {}
    region = data.get("f128") or ""
    if region.endswith("板块"):
        region = region[:-2]
    return {"industry": data.get("f127") or "", "region": region}

def save(date, src, targets):
    EXTRA_F.write_text(json.dumps({"_date": date, "_src": src, "targets": targets},
                                  ensure_ascii=False), "utf-8")

def main():
    d = json.loads((BASE / "section_data.json").read_text("utf-8"))
    cur = json.loads((BASE / "current_pool.json").read_text("utf-8"))
    date = d["cur_date"]
    hybk = {s["code"]: s["tags"][0] for s in cur["stocks"] if s.get("tags")}
    targets = {}  # code -> {"industry":..., "region":..., "concepts":[...]}
    for c in d["cur_cards"] + d["his_cards"]:
        targets.setdefault(c["code"], {"industry": hybk.get(c["code"], ""), "region": "", "concepts": []})
    cur_codes = {c["code"] for c in d["cur_cards"]}
    # 断点续跑:仅限同一天(领涨概念按当日涨幅,跨天必须重扫);已有数据保留,只补缺的
    if EXTRA_F.exists():
        old = json.loads(EXTRA_F.read_text("utf-8"))
        old_t = old.get("targets", old)  # 兼容无 _date 的旧格式
        if old.get("_date", date) == date:
            for code, v in old_t.items():
                if code in targets:
                    targets[code]["concepts"] = v.get("concepts") or targets[code]["concepts"]
                    targets[code]["industry"] = targets[code]["industry"] or v.get("industry", "")
                    targets[code]["region"] = v.get("region", "")
    print(f"目标股票 {len(targets)} 只(概念只取当前侧 {len(cur_codes)} 只)")

    src = "em" if push2_alive() else "kpl"
    print(f"概念源: {'东财板块反扫' if src == 'em' else 'push2 限流,兜底用开盘啦当日详情[12]'}")

    if src == "em":
        boards = all_concept_boards()
        print(f"概念板块 {len(boards)} 个(已去元板块),领涨: {[b['f14'] for b in boards[:3]]}")
        need = {c for c in cur_codes if len(targets[c]['concepts']) < 2}
        for i, b in enumerate(boards):
            if not need:
                break
            cons = clist(fs=f"b:{b['f12']}", fields="f12")
            hit = need & {s["f12"] for s in cons}
            for code in hit:
                targets[code]["concepts"].append(b["f14"])
            need = {c for c in need if len(targets[c]["concepts"]) < 2}
            if (i + 1) % 20 == 0:
                save(date, src, targets)
                print(f"  已扫 {i+1}/{len(boards)} 板块,缺概念 {len(need)} 只")
            time.sleep(0.3)
        print(f"概念扫描完成,仍缺 {len(need)} 只(冷门股只挂靠低涨幅板块)")
    else:
        got = concepts_from_kaipanla(date, cur_codes)
        if not got:
            src = "hybk"
        for code, tags in got.items():
            if not targets[code]["concepts"]:
                targets[code]["concepts"] = tags
        print(f"开盘啦概念回填 {len(got)}/{len(cur_codes)}")

    save(date, src, targets)
    miss_profile = [c for c, v in targets.items() if not v["industry"] or not v["region"]]
    if src == "em":
        for i, code in enumerate(miss_profile):
            profile = profile_of(code)
            targets[code]["industry"] = targets[code]["industry"] or profile["industry"]
            targets[code]["region"] = targets[code]["region"] or profile["region"]
            if (i + 1) % 20 == 0:
                save(date, src, targets)
            time.sleep(0.25)
        print(f"行业/地域补齐 {len(miss_profile)} 只")
    elif miss_profile:
        print(f"push2 限流,{len(miss_profile)} 只股票缺失的行业/地域留空(解封后重跑本脚本补齐)")

    save(date, src, targets)
    empty_c = sum(1 for c in cur_codes if not targets[c]["concepts"])
    empty_i = sum(1 for v in targets.values() if not v["industry"])
    empty_r = sum(1 for v in targets.values() if not v["region"])
    print(f"完成:当前侧无概念 {empty_c} 只,无行业 {empty_i} 只,无地域 {empty_r} 只")

if __name__ == "__main__":
    main()
