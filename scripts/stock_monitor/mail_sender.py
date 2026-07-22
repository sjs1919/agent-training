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


def build_summary_html(market_summary: str, stock_summaries: dict) -> str:
    """AI摘要 → HTML 邮件。"""
    stock_rows = ""
    for code, summary in stock_summaries.items():
        stock_rows += f"<tr><td style='white-space:nowrap'>{code}</td><td>{summary}</td></tr>"

    return f"""
    <html><body style='font-family:Microsoft YaHei,sans-serif;padding:20px'>
    <h2>📊 当日市场整体走势</h2>
    <p style='font-size:15px;line-height:1.8'>{market_summary}</p>
    <h2>📈 自选股AI走势摘要</h2>
    <table border='1' cellpadding='8' cellspacing='0' style='border-collapse:collapse;width:100%'>
    <tr style='background:#f0f0f0'><th style='width:100px'>代码</th><th>AI摘要</th></tr>
    {stock_rows}
    </table>
    <p style='color:#999;margin-top:20px'>🤖 以上摘要由 AI 基于真实行情数据生成，仅供参考，不构成投资建议。</p>
    <p style='color:#999'>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </body></html>"""
