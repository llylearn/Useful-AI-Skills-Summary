# -*- coding: utf-8 -*-
"""把 derive.render() 的 Markdown 中间结果包装成自包含 HTML 报告。"""
import html

import markdown


STYLE = """
*{box-sizing:border-box}
html{background:#f4f6f8}
body{margin:0;background:#f4f6f8;color:#24292f;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.6}
.report{width:100%;max-width:1500px;margin:24px auto;padding:0 24px 32px}
h1{margin:0 0 7px;font-size:23px;line-height:1.4;color:#202124}
.meta{margin:0 0 16px;color:#6b7280;font-size:13px}
.table-scroll{width:100%;overflow-x:auto;background:#fff;border:1px solid #e3e8ee;border-radius:12px;box-shadow:0 4px 18px rgba(31,41,55,.05)}
table{width:100%;min-width:880px;border-collapse:collapse;font-size:14px;line-height:1.65}
th,td{padding:13px 16px;border-bottom:1px solid #e8edf1;text-align:left;vertical-align:top;overflow-wrap:anywhere}
th{background:#f7f9fb;color:#4b5563;font-weight:650;white-space:nowrap}
td:first-child{width:46%;min-width:360px}
td:nth-child(2),td:nth-child(4){white-space:nowrap}
td:nth-child(3){min-width:160px}
td:nth-child(4){width:110px}
tbody tr:last-child td{border-bottom:0}
tbody tr:hover td{background:#f8fbff}
strong{color:#b52f37;font-weight:650}
.count{color:#8a94a3;font-size:12px}
.badge{display:inline-block;margin:3px 5px 0 0;padding:1px 7px;border-radius:999px;font-size:11px;line-height:1.6;white-space:nowrap}
.primary{background:#fff0f0;color:#b52f37;border:1px solid #f1c6c9}
.recent{background:#edf5ff;color:#2766a5;border:1px solid #c9def4}
.counter{background:#f1f3f5;color:#68707a;border:1px solid #dce1e6}
.in{display:inline-block;margin-left:6px;padding:0 5px;border-radius:4px;background:#fff1f2;color:#b52f37;font-size:11px;line-height:1.6;white-space:nowrap}
.muted{color:#8a94a3}
blockquote{margin:12px 2px 0;color:#7a828c;font-size:12px;line-height:1.6}
blockquote p{margin:0}
@media(max-width:640px){.report{margin:14px auto;padding:0 12px 22px}h1{font-size:20px}.meta{font-size:12px;margin-bottom:12px}.table-scroll{border-radius:9px}table{min-width:780px;font-size:13px}th,td{padding:10px 12px}td:first-child{min-width:320px}blockquote{font-size:11px}}
@media print{html,body{background:#fff}.report{max-width:none;margin:0;padding:0}.table-scroll{overflow:visible;box-shadow:none}table{min-width:0;font-size:10px}th,td{padding:7px}tr{break-inside:avoid}}
"""


def render_html(md_text, title):
    """生成无外部 CSS/JS/字体依赖的单文件 HTML。"""
    body = markdown.markdown(md_text, extensions=["tables", "sane_lists"])
    body = body.replace("<table>", '<div class="table-scroll"><table>').replace("</table>", "</table></div>")
    return ("<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n"
            "<meta charset=\"UTF-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1.0\">\n"
            f"<title>{html.escape(title)}</title>\n<style>{STYLE}</style>\n"
            f"</head>\n<body>\n<main class=\"report\">\n{body}\n</main>\n</body>\n</html>\n")
