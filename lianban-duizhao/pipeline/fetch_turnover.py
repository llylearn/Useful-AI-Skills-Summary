# -*- coding: utf-8 -*-
"""补齐当前/历史对照卡的全天成交额 -> turnover_amount.json。

主源：开盘啦 DailyLimitPerformance 行[11]，单位元。
兜底：腾讯 newfqkline 指定日 K 线行[8]，单位万元，转换为元；用于北交所等开盘啦未覆盖股票。
只接受 K 线日期与请求日期完全一致的数据，找不到时保留缺失，不做估算。
"""
import json
import sys
import time
from pathlib import Path

import requests

from fetch_kaipan_detail import fetch_detail

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent
OUT = BASE / "turnover_amount.json"


def tx_symbol(code):
    if code.startswith(("8", "4", "920")):
        return "bj" + code
    return ("sh" if code.startswith(("5", "6", "9")) else "sz") + code


def tencent_turnover(code, date):
    """腾讯指定日全天成交额；日K[8]单位为万元。"""
    symbol = tx_symbol(code)
    r = requests.get(
        "https://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfqkline/get",
        params={"param": f"{symbol},day,{date},{date},1,qfq"},
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com/"},
        timeout=25,
    )
    r.raise_for_status()
    data = (r.json().get("data") or {}).get(symbol) or {}
    rows = data.get("day") or data.get("qfqday") or []
    for row in rows:
        if len(row) > 8 and row[0] == date and row[8] not in (None, ""):
            return float(row[8]) * 10000
    return None


def main():
    d = json.loads((BASE / "section_data.json").read_text("utf-8"))
    result = {"_source": "开盘啦[11](元);缺失时腾讯newfqkline[8](万元转元)", "dates": {}}
    for date, cards in ((d["cur_date"], d["cur_cards"]), (d["his_date"], d["his_cards"])):
        detail = fetch_detail(date)
        amounts, sources = {}, {}
        missing = []
        for c in cards:
            code = c["code"]
            value = (detail.get(code) or {}).get("turnover_amount")
            if value is not None:
                amounts[code] = value
                sources[code] = "kpl"
            else:
                missing.append(code)
        for i, code in enumerate(missing, 1):
            value = None
            for attempt in range(3):
                try:
                    value = tencent_turnover(code, date)
                    break
                except Exception as exc:
                    print(f"  {date} {code} 腾讯第{attempt + 1}次失败: {exc}", flush=True)
                    time.sleep(attempt + 1)
            if value is not None:
                amounts[code] = value
                sources[code] = "tencent"
            time.sleep(0.12)
        result["dates"][date] = amounts
        result[f"_source_{date}"] = sources
        still_missing = [c["code"] for c in cards if c["code"] not in amounts]
        print(f"{date} 成交额 {len(amounts)}/{len(cards)}；开盘啦 {sum(v == 'kpl' for v in sources.values())}，"
              f"腾讯 {sum(v == 'tencent' for v in sources.values())}；缺 {still_missing}", flush=True)
        OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), "utf-8")
    print(f"输出 {OUT}")


if __name__ == "__main__":
    main()
