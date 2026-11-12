# -*- coding: utf-8 -*-
"""构建后自检(Python 层):
1. compare 元数据与页面一致(对照日、共同数)
2. 卡片数 = 当前 + 历史;共同卡 = 共同股 x 2
3. 历史对照日早于周期起点;历史日 total <= MAX_HIS
4. 每张卡都有 DETAIL;历史卡 zbc 为 "";标签<=2 且无代码/详情字样
"""
import json, re, sys, html, math
from pathlib import Path
from build import seal_lines

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent

def main():
    d = json.loads((BASE / "section_data.json").read_text("utf-8"))
    page = (BASE / f"对比看板_{d['cur_date']}.html").read_text("utf-8")

    assert d["his_date"] in page, "对照日未写入页面"
    assert d["his_date"] < d["cycle_start"], f'对照日 {d["his_date"]} 必须早于周期起点 {d["cycle_start"]}'

    hist = json.loads((BASE / "kaipan_history.json").read_text("utf-8"))
    assert hist[d["his_date"]]["total"] <= d["max_his"], "历史日超过 MAX_HIS"
    assert hist[d["his_date"]].get("detail") is True, "历史日缺详情"

    cards = re.findall(r'class="c-card[ "]', page)
    n_exp = len(d["cur_cards"]) + len(d["his_cards"])
    assert len(cards) == n_exp, f"卡片数 {len(cards)} != {n_exp}"
    common = re.findall(r'class="c-card common"', page)
    assert len(common) == d["n_common"] * 2, f"共同卡 {len(common)} != {d['n_common']}*2"

    assert '"zbc": ""' in page, "历史卡 zbc 应为空串(弹窗显示 —)"
    assert "详情" not in page, "页面不应出现「详情」"
    for c in d["cur_cards"] + d["his_cards"]:
        assert len(c["tags"]) <= 2
        assert "region" in c, f'{c["name"]} 缺地域字段'
        if c["region"]:
            region = html.escape(str(c["region"]), quote=True)
            assert f'<span class="region tag tag-region">{region}</span>' in page, f'{c["name"]} 地域 tag 未写入页面'
        if c.get("industry"):
            industry = html.escape(str(c["industry"]), quote=True)
            assert f'<span class="ind tag tag-industry">{industry}</span>' in page, f'{c["name"]} 行业 tag 未写入页面'
        for tag in c["tags"]:
            tag_text = html.escape(str(tag), quote=True)
            assert f'<span class="tag tag-concept">{tag_text}</span>' in page, f'{c["name"]} 概念 tag 未写入页面'
        amount = c.get("order_amount")
        turnover = c.get("turnover_amount")
        pct = c.get("seal_turnover_pct")
        if amount is None or turnover is None:
            assert pct is None, f'{c["name"]} 缺封单额或成交额时不应计算封成比'
        else:
            expected_pct = float(amount) / float(turnover) * 100
            assert pct is not None and math.isclose(pct, expected_pct, rel_tol=1e-12), f'{c["name"]} 封单额/成交额换算错误'
            assert re.search(r"\d+\.\d{2}%$", seal_lines(c)[2]), f'{c["name"]} 封成比未保留两位小数'
        for line in seal_lines(c):
            seal_line = html.escape(line, quote=True)
            assert f'<span class="seal-line">{seal_line}</span>' in page, f'{c["name"]} 封单/成交/占比未写入卡片'
        assert f'{c["side"]}_{c["code"]}' in page, f'{c["name"]} 缺 DETAIL'
    seals = re.findall(r'class="seal"', page)
    assert len(seals) == n_exp, f"封单区块 {len(seals)} != {n_exp}"
    seal_line_count = len(re.findall(r'class="seal-line"', page))
    assert seal_line_count == n_exp * 3, f"封单/成交/占比行 {seal_line_count} != {n_exp * 3}"
    assert "万手" not in page and "亿手" not in page, "新看板不应再显示封单手数"
    for empty_tag in ('class="region tag tag-region"></span>',
                      'class="ind tag tag-industry"></span>',
                      'class="tag tag-concept"></span>'):
        assert empty_tag not in page, "页面不应出现空 tag"
    for c in d["his_cards"]:
        assert c["zbc"] is None
    for c in d["cur_cards"]:
        assert c["zbc"] is not None

    print("Python 层自检全部通过 ✓")
    print(json.dumps({"hdate": d["his_date"], "n_common": d["n_common"],
                      "cards": len(cards), "common_cards": len(common),
                      "seal_blocks": len(seals), "seal_lines": seal_line_count,
                      "turnover_ok": sum(c.get("turnover_amount") is not None for c in d["cur_cards"] + d["his_cards"]),
                      "pct_ok": sum(c.get("seal_turnover_pct") is not None for c in d["cur_cards"] + d["his_cards"])}, ensure_ascii=False))

if __name__ == "__main__":
    main()
