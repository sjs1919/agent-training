"""测试邮件发送 - 验证 QQ SMTP 通道是否正常"""
import sys
from scripts.stock_monitor.config import load_config
from scripts.stock_monitor.mail_sender import send_email
from datetime import datetime

config = load_config()
body = f"""<html><body>
<h2>📊 部署验证测试</h2>
<p>stock-monitor 容器已成功部署于 token_hub_47。</p>
<p>自选股({len(config.stocks)}只): {', '.join(config.stocks)}</p>
<p>LLM Provider: 火山豆包 + DeepSeek 备用</p>
<p>监控时段: {config.monitor.trading_start}-{config.monitor.trading_end}，每{config.monitor.check_interval_seconds}秒轮询</p>
<p>邮件通道: QQ SMTP ({config.email.smtp_host})</p>
<p>时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</body></html>"""

ok = send_email(config.email, f'部署验证测试 {datetime.now().strftime("%Y-%m-%d %H:%M")}', body)
print('邮件发送: OK' if ok else '邮件发送: FAILED')
