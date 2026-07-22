"""
主入口：交易日判断 → 盘中均线监控(信号邮件告警) → 收盘AI摘要(邮件发送)
启动方式: cd projects/agent-training && python -m scripts.stock_monitor.main
"""
import sys
import time
from datetime import datetime, time as dtime
from typing import List

from scripts.stock_monitor.config import load_config, AppConfig, get_enabled_providers
from scripts.stock_monitor.llm_client import init_clients, close_clients
from scripts.stock_monitor.data_fetcher import (
    get_code_name_map,
    get_realtime_quotes,
    get_latest_ma_values,
)
from scripts.stock_monitor.ma_monitor import MAMonitor, MASignal
from scripts.stock_monitor.summarizer import generate_market_summary, generate_all_summaries
from scripts.stock_monitor.mail_sender import send_email, build_signals_html, build_summary_html


def is_trading_day() -> bool:
    """判断今天是否是交易日（周一至周五）。"""
    return datetime.now().weekday() < 5


def is_trading_time(start_str: str, end_str: str) -> bool:
    """判断当前时间是否在交易时段内。"""
    now = datetime.now().time()
    return dtime.fromisoformat(start_str) <= now <= dtime.fromisoformat(end_str)


def is_after_close(end_str: str) -> bool:
    """判断当前时间是否已过收盘时间。"""
    return datetime.now().time() > dtime.fromisoformat(end_str)


def run_monitor_loop(config: AppConfig):
    """盘中监控主循环。"""
    monitor = MAMonitor()
    name_map = get_code_name_map()
    close_sent = False

    print(f"[监控] 自选股({len(config.stocks)}只): {config.stocks}")
    print(f"[监控] 时间: {config.monitor.trading_start}-{config.monitor.trading_end}, "
          f"间隔: {config.monitor.check_interval_seconds}s")

    if is_after_close(config.monitor.trading_end):
        send_close_summary(config)
        return

    while is_trading_time(config.monitor.trading_start, config.monitor.trading_end):
        try:
            df_quotes = get_realtime_quotes(config.stocks)
            all_signals: List[MASignal] = []

            for _, row in df_quotes.iterrows():
                code = row["代码"]
                name = row.get("名称", name_map.get(code, code))
                price = row["最新价"]
                ma_values = get_latest_ma_values(code)
                signals = monitor.check_stock(code, name, price, ma_values)
                for sig in signals:
                    monitor.clear_reverse(sig.code, sig.ma_type, sig.direction)
                all_signals.extend(signals)

            if all_signals:
                print(f"[信号] {len(all_signals)}条")
                for sig in all_signals:
                    print(f"  {sig.timestamp} {sig.name} {sig.direction}{sig.ma_type} 价格{sig.price}")
                html = build_signals_html(all_signals)
                send_email(config.email, f"盘中信号-{len(all_signals)}条", html)

        except Exception as e:
            print(f"[监控] 轮询异常: {e}")

        time.sleep(config.monitor.check_interval_seconds)

    if not close_sent:
        send_close_summary(config)


def send_close_summary(config: AppConfig):
    """收盘后：调用 LLM 生成摘要 → 邮件发送。"""
    print("\n[摘要] 收盘，LLM 正在生成 AI 摘要...")
    try:
        market = generate_market_summary(config)
        stocks = generate_all_summaries(config)
        html = build_summary_html(market, stocks)
        send_email(config.email, f"收盘AI摘要-{datetime.now().strftime('%Y-%m-%d')}", html)
        print("[摘要] ✅ 收盘AI摘要已发送")
    except Exception as e:
        print(f"[摘要] ❌ 失败: {e}")


def main():
    """主入口：24/7 运行，交易时间监控，非交易时间休眠。"""
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    config = load_config()
    if not config.stocks:
        print("[错误] sock.yml 未配置自选股")
        return

    providers = get_enabled_providers(config)
    if not providers:
        print("[警告] 无可用LLM provider，摘要将使用数据拼接模式")
    else:
        init_clients(config)

    print(f"[监控] 守护进程启动，自选股({len(config.stocks)}只): {config.stocks}")

    try:
        while True:  # 24/7 外层循环，Docker 容器长期运行
            if not is_trading_day():
                print(f"[监控] 非交易日({datetime.now().strftime('%Y-%m-%d')})，休眠1小时后重试...")
                time.sleep(3600)
                continue

            if not is_trading_time(config.monitor.trading_start, config.monitor.trading_end):
                time.sleep(60)
                continue

            print(f"[监控] 进入交易时段，开始监控")
            run_monitor_loop(config)
            # run_monitor_loop 在收盘后返回，休眠等待次日
    finally:
        close_clients()


if __name__ == "__main__":
    main()
