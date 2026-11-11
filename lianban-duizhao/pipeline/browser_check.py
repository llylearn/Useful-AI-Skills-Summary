# -*- coding: utf-8 -*-
"""浏览器层自检(headless Chrome + CDP):
- 1440 / 390 两档宽度查横向溢出
- .c-card 数量 = 当前+历史;.c-card.common = 共同股 x 2
- .tags 无横向溢出
- 点历史最高板卡:zbc 显示 —、几天几板非空
- 点当前最高板卡:zbc 显示 N 次
- 页面无 JS 报错
"""
import json, os, shutil, subprocess, sys, time, urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent
CHROME = (os.environ.get("CHROME_BIN") or shutil.which("google-chrome")
          or shutil.which("google-chrome-stable") or shutil.which("chromium"))
PORT = 9223

import websocket

def ev(ws, expr, mid=[0]):
    mid[0] += 1
    ws.send(json.dumps({"id": mid[0], "method": "Runtime.evaluate",
                        "params": {"expression": expr, "returnByValue": True}}))
    while True:
        m = json.loads(ws.recv())
        if m.get("id") == mid[0]:
            r = m.get("result", {}).get("result", {})
            if m.get("result", {}).get("exceptionDetails"):
                raise AssertionError("JS 异常: " + json.dumps(m["result"]["exceptionDetails"], ensure_ascii=False)[:300])
            return r.get("value")

def set_width(ws, w, mid=[1000]):
    mid[0] += 1
    ws.send(json.dumps({"id": mid[0], "method": "Emulation.setDeviceMetricsOverride",
                        "params": {"width": w, "height": 900, "deviceScaleFactor": 1, "mobile": w < 500}}))
    while True:
        m = json.loads(ws.recv())
        if m.get("id") == mid[0]:
            return

def main():
    if not CHROME:
        raise SystemExit("未找到 Chrome；请安装 google-chrome 或设置 CHROME_BIN")
    d = json.loads((BASE / "section_data.json").read_text("utf-8"))
    url = (BASE / f"对比看板_{d['cur_date']}.html").as_uri()
    cmd = [CHROME, "--headless=new", "--disable-gpu",
           f"--remote-debugging-port={PORT}", "--remote-allow-origins=*",
           "--user-data-dir=" + str(BASE / ".chrome-cdp"), "--no-first-run", "about:blank"]
    if os.environ.get("CHROME_NO_SANDBOX") == "1":
        cmd.insert(1, "--no-sandbox")
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        target = None
        for _ in range(40):
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{PORT}/json/new?{url}", method="PUT")
                target = json.loads(urllib.request.urlopen(req, timeout=2).read())
                break
            except Exception:
                time.sleep(0.5)
        if not target:
            raise RuntimeError("CDP 连接失败")
        ws = websocket.create_connection(target["webSocketDebuggerUrl"], timeout=20)
        time.sleep(2)

        n_cards = len(d["cur_cards"]) + len(d["his_cards"])
        for w in (1440, 390):
            set_width(ws, w)
            time.sleep(0.6)
            sw = ev(ws, "document.body.scrollWidth")
            iw = ev(ws, "window.innerWidth")
            assert sw <= iw, f"{w}px 横向溢出: scrollWidth={sw} > innerWidth={iw}"
            nc = ev(ws, "document.querySelectorAll('.c-card').length")
            assert nc == n_cards, f"{w}px 卡片数 {nc} != {n_cards}"
            ncm = ev(ws, "document.querySelectorAll('.c-card.common').length")
            assert ncm == d["n_common"] * 2, f"{w}px 共同卡 {ncm} != {d['n_common']*2}"
            nr = ev(ws, "document.querySelectorAll('.c-card .region.tag-region').length")
            nr_exp = sum(bool(c.get("region")) for c in d["cur_cards"] + d["his_cards"])
            assert nr == nr_exp, f"{w}px 地域数 {nr} != {nr_exp}"
            ni = ev(ws, "document.querySelectorAll('.c-card .tag-industry').length")
            ni_exp = sum(bool(c.get("industry")) for c in d["cur_cards"] + d["his_cards"])
            assert ni == ni_exp, f"{w}px 行业 tag 数 {ni} != {ni_exp}"
            nt = ev(ws, "document.querySelectorAll('.c-card .tag-concept').length")
            nt_exp = sum(len(c["tags"][:2]) for c in d["cur_cards"] + d["his_cards"])
            assert nt == nt_exp, f"{w}px 概念 tag 数 {nt} != {nt_exp}"
            ns = ev(ws, "document.querySelectorAll('.c-card .seal').length")
            assert ns == n_cards, f"{w}px 封单行 {ns} != {n_cards}"
            colors = ev(ws, """['region','industry','concept'].map(k=>{
                const e=document.querySelector('.tag-'+k);if(!e)return null;
                const s=getComputedStyle(e);return [s.backgroundColor,s.color]})""")
            expected_colors = [
                ["rgb(232, 241, 251)", "rgb(53, 107, 154)"],
                ["rgb(255, 240, 217)", "rgb(139, 91, 22)"],
                ["rgb(255, 237, 213)", "rgb(194, 65, 12)"],
            ]
            assert colors == expected_colors, f"{w}px tag 配色异常: {colors}"
            non_white = ev(ws, """[...document.querySelectorAll('.c-card')]
                .filter(e=>getComputedStyle(e).backgroundColor!=='rgb(255, 255, 255)').length""")
            assert non_white == 0, f"{w}px 有 {non_white} 张卡片不是白色背景"
            bad_common_border = ev(ws, """[...document.querySelectorAll('.c-card.common')].filter(e=>{
                const s=getComputedStyle(e);
                return s.borderTopColor!=='rgb(53, 107, 154)'||s.borderTopWidth!=='2px'}).length""")
            assert bad_common_border == 0, f"{w}px 有 {bad_common_border} 张共同卡未使用 2px 蓝框"
            bad_order = ev(ws, """[...document.querySelectorAll('.c-card')].filter(e=>{
                const r=e.querySelector('.region'),s=e.querySelector('.l,.w');
                return r&&s&&!(r.compareDocumentPosition(s)&Node.DOCUMENT_POSITION_FOLLOWING)}).length""")
            assert bad_order == 0, f"{w}px 有 {bad_order} 张卡片地域未放在输赢前"
            bad = ev(ws, "[...document.querySelectorAll('.tags')].filter(t=>t.scrollWidth>t.clientWidth).length")
            assert bad == 0, f"{w}px 有 {bad} 个 .tags 溢出"
            bad_seal = ev(ws, "[...document.querySelectorAll('.seal')].filter(t=>t.scrollWidth>t.clientWidth).length")
            assert bad_seal == 0, f"{w}px 有 {bad_seal} 个封单行溢出"
            bad_seal_order = ev(ws, """[...document.querySelectorAll('.c-card')].filter(e=>{
                const wl=e.querySelector('.wl'),seal=e.querySelector('.seal'),tags=e.querySelector('.tags');
                return !wl||!seal||!tags||!(wl.compareDocumentPosition(seal)&Node.DOCUMENT_POSITION_FOLLOWING)
                    ||!(seal.compareDocumentPosition(tags)&Node.DOCUMENT_POSITION_FOLLOWING)}).length""")
            assert bad_seal_order == 0, f"{w}px 有 {bad_seal_order} 张卡片封单行不在地域行和概念行之间"
            print(f"{w}px:无横向溢出,卡片 {nc},共同卡 {ncm},地域 {nr} 且在输赢前,封单行 {ns} 且无溢出,tags 无溢出 ✓")

        set_width(ws, 1440)
        time.sleep(0.5)
        # 历史最高板卡
        his_max = max(c["lb"] for c in d["his_cards"])
        ev(ws, f"""(()=>{{const el=[...document.querySelectorAll('.c-card')]
            .find(e=>{{const k=DETAIL[e.dataset.key];return k.side==='his'&&k.lb==={his_max}}});
            el.click();return true}})()""")
        time.sleep(0.3)
        zbc = ev(ws, "document.getElementById('m-zbc').textContent")
        days = ev(ws, "document.getElementById('m-days').textContent")
        sub = ev(ws, "document.getElementById('m-sub').textContent")
        assert zbc == "—", f"历史卡炸板应为 —,实为 {zbc}"
        assert days and days != "—", "历史卡几天几板为空"
        print(f"历史 {his_max} 板卡弹窗:炸板=—,几天几板={days},{sub} ✓")
        ev(ws, "document.getElementById('close').click()")

        # 当前最高板卡
        cur_max = max(c["lb"] for c in d["cur_cards"])
        ev(ws, f"""(()=>{{const el=[...document.querySelectorAll('.c-card')]
            .find(e=>{{const k=DETAIL[e.dataset.key];return k.side==='cur'&&k.lb==={cur_max}}});
            el.click();return true}})()""")
        time.sleep(0.3)
        zbc = ev(ws, "document.getElementById('m-zbc').textContent")
        assert zbc.endswith(" 次"), f"当前卡炸板应为 N 次,实为 {zbc}"
        print(f"当前 {cur_max} 板卡弹窗:炸板={zbc} ✓")

        errs = ev(ws, "window.__errs||0")
        assert not errs, "页面有 JS 报错"
        print("浏览器层自检全部通过 ✓")
        ws.close()
    finally:
        proc.terminate()

if __name__ == "__main__":
    main()
