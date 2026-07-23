"""
邮件发送模块：QQ SMTP 发送 HTML 邮件。
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

from scripts.stock_monitor.config import EmailConfig


def send_email(config: EmailConfig, subject: str, html_body: str) -> bool:
    """发送HTML邮件。收件人从 config.to_emails 读取。"""
    if not config.enabled:
        print("[邮件] 已禁用")
        return False
    if not config.to_emails:
        print("[邮件] 收件人未配置")
        return False
    if not config.username or not config.password:
        print("[邮件] SMTP账号密码未配置")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"{config.subject_prefix} {subject}"
        msg["From"] = f"{config.from_name} <{config.username}>"
        msg["To"] = ", ".join(config.to_emails)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=30) as server:
            server.starttls()
            server.login(config.username, config.password)
            server.sendmail(config.username, config.to_emails, msg.as_string())

        print(f"[邮件] ✅ 发送成功: {subject}")
        return True
    except Exception as e:
        print(f"[邮件] ❌ 发送失败: {e}")
        return False


def build_signals_html(signals: list, title: str = "盘中均线信号告警") -> str:
    """均线信号 → HTML 邮件。"""
    if not signals:
        return f"<h2>{title}</h2><p>当前无触发信号。</p>"

    rows = ""
    for sig in signals:
        color = "#e74c3c" if "跌破" in sig.direction else "#27ae60"
        rows += (
            f"<tr><td>{sig.timestamp}</td><td>{sig.code} {sig.name}</td>"
            f"<td>{sig.price}</td><td>{sig.ma_type}({sig.ma_value})</td>"
            f"<td style='color:{color};font-weight:bold'>{sig.direction}</td></tr>"
        )

    return f"""
    <html><body>
    <h2>🔔 {title}</h2>
    <table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>
    <tr style='background:#f0f0f0'><th>时间</th><th>股票</th><th>价格</th><th>均线</th><th>方向</th></tr>
    {rows}
    </table>
    <p><em>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>
    </body></html>"""


def _fmt(val, decimals=2) -> str:
    """安全格式化数值。"""
    if val is None:
        return "-"
    return f"{val:+.{decimals}f}" if isinstance(val, float) and decimals > 0 else f"{val}"


def _fmt_amount(amount) -> str:
    """格式化成交额：元→亿。"""
    if amount is None:
        return "-"
    return f"{amount / 1e8:.2f}亿"


def _color(val, is_pct=True) -> str:
    """涨跌颜色：红涨绿跌。"""
    if val is None:
        return "#666"
    if val > 0:
        return "#e74c3c"
    elif val < 0:
        return "#27ae60"
    return "#666"


def build_summary_html(summary: dict) -> str:
    """
    收盘总结 → 富文本 HTML 邮件。
    格式：大盘概况表 + 市场特征 + 自选股表 + 后市展望。
    """
    market_table = summary.get("market_table", {})
    characteristics = summary.get("market_characteristics", "")
    stock_table = summary.get("stock_table", [])
    outlook = summary.get("outlook", "")
    today = datetime.now().strftime("%Y年%m月%d日")

    # ── 大盘概况表格 ──
    index_rows = ""
    for idx in market_table.get("indices", []):
        amt_chg = idx.get("amount_chg_pct")
        amt_chg_str = _fmt(amt_chg) + "%" if amt_chg is not None else "-"
        index_rows += f"""
        <tr>
            <td>{idx['name']}</td>
            <td>{_fmt(idx.get('close'))}</td>
            <td style="color:{_color(idx.get('change_pct'))}">{_fmt(idx.get('change_pct'))}%</td>
            <td>{_fmt_amount(idx.get('amount'))}</td>
            <td style="color:{_color(amt_chg)}">{amt_chg_str}</td>
        </tr>"""

    index_html = f"""
    <h2>📊 大盘概况</h2>
    <table cellpadding="8" cellspacing="0" style="border-collapse:collapse;width:100%">
    <tr style="background:#f0f0f0">
        <th>指数</th><th>收盘价</th><th>涨跌幅</th><th>成交额</th><th>成交额变化</th>
    </tr>{index_rows}
    </table>
    <p style="color:#999;font-size:13px;margin-top:5px">
        全市场成交额（上证+深证）：{_fmt_amount(market_table.get('total_amount'))}
        {(' 环比' + _fmt(market_table.get('total_amount_chg_pct')) + '%') if market_table.get('total_amount_chg_pct') is not None else ''}
    </p>"""

    # ── 市场特征 ──
    char_lines = characteristics.split("\n")
    char_html = "<br>".join(
        f"<span style='font-size:14px;line-height:2.0'>{line.strip()}</span>"
        for line in char_lines if line.strip()
    )

    # ── 自选股表格 ──
    stock_rows = ""
    for s in stock_table:
        if s.get("error"):
            stock_rows += f"<tr><td>{s['code']}</td><td>{s['name']}</td><td colspan='6' style='color:#999'>{s['error']}</td></tr>"
            continue
        stock_rows += f"""
        <tr>
            <td>{s['code']}</td>
            <td>{s['name']}</td>
            <td>{_fmt(s.get('close'))}</td>
            <td style="color:{_color(s.get('change_pct'))};font-weight:bold">{_fmt(s.get('change_pct'))}%</td>
            <td>{_fmt_amount(s.get('amount'))}</td>
            <td>{_fmt(s.get('turnover'))}%</td>
            <td>{_fmt(s.get('amplitude'), 1)}%</td>
            <td style="font-size:12px">{s.get('ma_relation', '-')}</td>
            <td style="font-size:12px">{s.get('trend', '-')}</td>
        </tr>"""

    stock_html = f"""
    <h2>📈 自选股表现</h2>
    <table cellpadding="8" cellspacing="0" style="border-collapse:collapse;width:100%">
    <tr style="background:#f0f0f0">
        <th>代码</th><th>名称</th><th>收盘价</th><th>涨跌幅</th><th>成交额</th><th>换手率</th><th>振幅</th><th>均线关系</th><th>走势特征</th>
    </tr>{stock_rows}
    </table>"""

    # ── 后市展望 ──
    outlook_paras = outlook.replace("\n\n", "</p><p>").replace("\n", "<br>")
    outlook_html = f"""
    <h2>🔮 后市展望</h2>
    <p style="font-size:14px;line-height:1.8">{outlook_paras}</p>"""

    # ── 组装 ──
    return f"""
    <html><body style="font-family:Microsoft YaHei,sans-serif;padding:20px;max-width:800px">
    <h1 style="border-bottom:2px solid #333;padding-bottom:10px">📈 {today} A股收盘总结</h1>
    {index_html}
    <h2>📋 今日市场特征</h2>
    <div style="background:#fafafa;padding:15px;border-radius:5px;line-height:2.0">{char_html}</div>
    {stock_html}
    {outlook_html}
    <hr style="margin-top:30px">
    <p style="color:#999;font-size:12px">🤖 以上数据由系统自动生成，市场特征与后市展望由 AI 基于真实行情数据撰写，仅供参考，不构成投资建议。</p>
    <p style="color:#999;font-size:12px">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </body></html>"""
