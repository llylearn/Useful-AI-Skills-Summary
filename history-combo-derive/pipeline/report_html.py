# -*- coding: utf-8 -*-
"""把 derive.render() 的 Markdown 中间结果包装成自包含 HTML 报告。"""
import html

import markdown


STYLE = """
*{box-sizing:border-box}
body{margin:0;background:#f4f6f8;color:#24292f;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.75}
.report{max-width:1280px;margin:0 auto;padding:28px 36px 40px;background:#fff;min-height:100vh}
h1{margin:0 0 18px;font-size:25px;line-height:1.4;color:#202124}
h2{margin:34px 0 14px;padding:8px 12px;border-left:4px solid #c93c3c;background:#faf2f2;font-size:19px;line-height:1.5}
h3{margin:24px 0 10px;font-size:16px;color:#454c54}
p{margin:9px 0}
strong{color:#b52f37;font-weight:650}
blockquote{margin:14px 0;padding:10px 14px;border-left:3px solid #9db3c8;background:#f4f7fa;color:#5b6670}
blockquote p{margin:2px 0}
hr{border:0;border-top:1px solid #e5e8eb;margin:22px 0}
ul,ol{padding-left:25px}
li{margin:6px 0}
li::marker{color:#9a4248;font-weight:600}
table{width:100%;margin:14px 0 20px;border-collapse:collapse;display:block;overflow-x:auto;font-size:13px;line-height:1.65}
th,td{padding:9px 10px;border:1px solid #e2e6ea;text-align:left;vertical-align:top;overflow-wrap:anywhere}
th{background:#f2f4f6;color:#414a53;font-weight:650;white-space:nowrap}
tr:nth-child(even) td{background:#fafbfb}
td:first-child{white-space:nowrap}
code{padding:1px 4px;border-radius:4px;background:#f0f2f4;font-family:Consolas,monospace}
@media(max-width:640px){.report{padding:18px 14px 28px}h1{font-size:21px}h2{font-size:17px;margin-top:26px}table{font-size:12px}th,td{padding:7px}}
@media print{body{background:#fff}.report{max-width:none;padding:0}h2{break-after:avoid}table{display:table;font-size:10px;overflow:visible}tr{break-inside:avoid}}
"""


def render_html(md_text, title):
    """生成无外部 CSS/JS/字体依赖的单文件 HTML。"""
    body = markdown.markdown(md_text, extensions=["tables", "sane_lists"])
    return ("<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n"
            "<meta charset=\"UTF-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1.0\">\n"
            f"<title>{html.escape(title)}</title>\n<style>{STYLE}</style>\n"
            f"</head>\n<body>\n<main class=\"report\">\n{body}\n</main>\n</body>\n</html>\n")
