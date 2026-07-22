"""
均线监控模块：盘中检测价格跌破/突破5、10、20日均线。
使用内存信号集合去重，支持反向信号重置。
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Set


@dataclass
class MASignal:
    code: str
    name: str
    price: float
    ma_type: str        # "MA5" / "MA10" / "MA20"
    ma_value: float
    direction: str      # "向上突破" or "向下跌破"
    timestamp: str      # "YYYY-MM-DD HH:MM:SS"


class MAMonitor:
    """均线监控器，去重避免同一信号重复告警。"""

    def __init__(self):
        self._triggered: Set[str] = set()

    def check_stock(self, code: str, name: str, current_price: float,
                    ma_values: Dict[str, float]) -> List[MASignal]:
        """检查单只股票的均线信号，返回新触发的信号列表（已去重）。"""
        new_signals: List[MASignal] = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for ma_type, ma_val in ma_values.items():
            if ma_val is None or ma_val <= 0:
                continue
            direction = "向上突破" if current_price >= ma_val else "向下跌破"
            signal_key = f"{code}_{ma_type}_{direction}"

            if signal_key not in self._triggered:
                self._triggered.add(signal_key)
                new_signals.append(MASignal(
                    code=code, name=name, price=current_price,
                    ma_type=ma_type, ma_value=round(ma_val, 2),
                    direction=direction, timestamp=now,
                ))
        return new_signals

    def reset_day(self):
        """新交易日清空已触发信号。"""
        self._triggered.clear()

    def clear_reverse(self, code: str, ma_type: str, direction: str):
        """清除反向信号，允许均线再次触发。"""
        reverse = "向下跌破" if direction == "向上突破" else "向上突破"
        self._triggered.discard(f"{code}_{ma_type}_{reverse}")
