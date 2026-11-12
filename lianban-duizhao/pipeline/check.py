# -*- coding: utf-8 -*-
"""构建后自检(Python 层):
1. compare 元数据与页面一致(对照日、共同数)
2. 卡片数 = 当前 + 历史;共同卡 = 共同股 x 2
3. 历史对照日早于周期起点;历史日 total <= MAX_HIS
4. 每张卡都有 DETAIL;历史卡 zbc 为 "";标签<=2 且无代码/详情字样
5. 新版式:hero 统计卡、对照七宫格、共同涨停胶囊、板数轴、终N板徽标齐全
"""
import json, re, sys, html, math
from pathlib import Path
from build import seal_text

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

    cards = re.findall(r'class="c-card(?: common)?"', page)
    n_exp = len(d["cur_cards"]) + len(d["his_cards"])
    assert len(cards) == n_exp, f"卡片数 {len(cards)} != {n_exp}"
    common = re.findall(r'class="c-card common"', page)
    assert len(common) == d["n_common"] * 2, f"共同卡 {len(common)} != {d['n_common']}*2"

    assert '"zbc": ""' in page, "历史卡 zbc 应为空串(弹窗显示 —)"
    assert "详情" not in page, "页面不应出现「详情」"

    # 版式骨架:hero 5 张统计卡 / 对照区 7 格 / 共同胶囊 / 板数轴 / 聚焦按钮 / 吸顶双栏头
    assert len(re.findall(r'class="stat(?: up| lb| top| broken)?"', page)) == 5, "hero 统计卡应为 5 张"
    assert len(re.findall(r'class="c-stat (?:cur|his|com)"', page)) == 7, "对照区统计格应为 7 格"
    n_chip = len(re.findall(r'class="c-chip"', page))
    assert n_chip == max(d["n_common"], 1), f"共同涨停胶囊 {n_chip} != {max(d['n_common'], 1)}"
    n_board = len({c["lb"] for c in d["cur_cards"] + d["his_cards"]})
    assert len(re.findall(r'class="c-rail"', page)) == n_board, "板数轴数量与页面层级不一致"
    assert 'id="cFocusBtn"' in page and "聚焦共同票" in page, "缺少聚焦共同票按钮"
    assert 'class="c-mhead"' in page, "缺少吸顶双栏头"
    for cls in ("c-side cur", "c-side his", "c-vs"):
        assert cls in page, f"吸顶双栏头缺少 {cls}"

    # 卡片:三类 tag / 封单行 / 终N板 / DETAIL
    fin_exp = 0
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
        amount, price, hands = c.get("order_amount"), c.get("close_price"), c.get("order_hands")
        if amount is None or price is None:
            assert hands is None, f'{c["name"]} 缺收盘价或封单额时不应手算手数'
        else:
            expected_hands = float(amount) / float(price) / 100
            assert hands is not None and math.isclose(hands, expected_hands, rel_tol=1e-12), f'{c["name"]} 封单手数换算错误'
        seal = html.escape(seal_text(c), quote=True)
        assert f'<div class="seal">{seal}</div>' in page, f'{c["name"]} 封单金额/手数未写入卡片'
        assert f'{c["side"]}_{c["code"]}' in page, f'{c["name"]} 缺 DETAIL'
        if c["side"] == "his" and c.get("final_lb"):
            fin_exp += 1
            assert f'终{c["final_lb"]}板' in page, f'{c["name"]} 缺终N板'
        # 有输赢才显示,且顺序为 输(绿) -> 赢(红)
        if c["losses_n"]:
            assert f'<span class="wl l" title="同梯队 3 板+，对手晋级而本股未晋级">输{c["losses_n"]}</span>' in page
        if c["wins_n"]:
            assert f'<span class="wl w" title="同梯队 3 板+，本股晋级而对手未晋级">赢{c["wins_n"]}</span>' in page
    assert len(re.findall(r'class="fin"', page)) == fin_exp, "终N板徽标数不一致"
    assert fin_exp == d["n_common"], f"共同历史卡终N板 {fin_exp} != 共同股 {d['n_common']}"

    seals = re.findall(r'class="seal"', page)
    assert len(seals) == n_exp, f"封单行 {len(seals)} != {n_exp}"
    for empty_tag in ('class="region tag tag-region"></span>',
                      'class="ind tag tag-industry"></span>',
                      'class="tag tag-concept"></span>'):
        assert empty_tag not in page, "页面不应出现空 tag"
    for c in d["his_cards"]:
        assert c["zbc"] is None
    for c in d["cur_cards"]:
        assert c["zbc"] is not None
    # 历史最高板与当前最高板在页面上都要有对应的板数轴
    assert f'<b>{max(c["lb"] for c in d["his_cards"])}</b><span>板</span>' in page
    assert f'<b>{max(c["lb"] for c in d["cur_cards"])}</b><span>板</span>' in page

    print("Python 层自检全部通过 ✓")
    print(json.dumps({"hdate": d["his_date"], "n_common": d["n_common"],
                      "cards": len(cards), "common_cards": len(common),
                      "seal_lines": len(seals), "chips": n_chip,
                      "boards": n_board, "final_badges": fin_exp}, ensure_ascii=False))


if __name__ == "__main__":
    main()
