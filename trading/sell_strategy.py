"""
매도 전략 모듈
"""
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
import time


class SellStrategy(QObject):
    """매도 전략 관리 클래스"""

    # 시그널 정의
    sell_order_sent = pyqtSignal(str, int, int, str)  # 종목코드, 수량, 가격, 매도사유
    sell_completed = pyqtSignal(str, int, int, float)  # 종목코드, 수량, 가격, 수익률

    def __init__(self, kiwoom_api, buy_strategy):
        super().__init__()
        self.api = kiwoom_api
        self.buy_strategy = buy_strategy

        # 매도 모니터링 타이머
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._monitor_stocks)
        self.monitor_timer.start(1000)  # 1초마다 체크

        # 트레일링 스탑 최고가 기록
        self.trailing_high_prices = {}

    def _monitor_stocks(self):
        """보유 종목 모니터링"""
        bought_stocks = self.buy_strategy.get_bought_stocks()

        for code, stock_info in list(bought_stocks.items()):
            self._check_sell_conditions(code, stock_info)

    def _check_sell_conditions(self, code, stock_info):
        """매도 조건 체크"""
        settings = stock_info['settings']
        current_price = self._get_current_price(code)

        if current_price == 0:
            return

        buy_price = stock_info['buy_price']
        profit_rate = ((current_price - buy_price) / buy_price) * 100

        # 1. 익절 체크
        if self._check_profit_cut(code, stock_info, current_price, profit_rate):
            return

        # 2. 손절 체크
        if self._check_loss_cut(code, stock_info, current_price, profit_rate):
            return

        # 3. 트레일링 스탑 체크
        if self._check_trailing_stop(code, stock_info, current_price, profit_rate):
            return

        # 4. 이익보존 체크
        if self._check_profit_protect(code, stock_info, current_price, profit_rate):
            return

        # 5. 시간 청산 체크
        if self._check_time_exit(code, stock_info):
            return

    def _check_profit_cut(self, code, stock_info, current_price, profit_rate):
        """익절 체크"""
        settings = stock_info['settings']

        if not settings.get('enable_profit_cut', False):
            return False

        profit_cut_rate = settings.get('profit_cut_rate', 5.0)

        if profit_rate >= profit_cut_rate:
            reason = f"익절({profit_rate:.2f}%)"
            self._execute_sell(code, stock_info, current_price, reason)
            return True

        return False

    def _check_loss_cut(self, code, stock_info, current_price, profit_rate):
        """손절 체크"""
        settings = stock_info['settings']

        if not settings.get('enable_loss_cut', False):
            return False

        loss_cut_rate = settings.get('loss_cut_rate', -3.0)

        if profit_rate <= loss_cut_rate:
            reason = f"손절({profit_rate:.2f}%)"
            self._execute_sell(code, stock_info, current_price, reason)
            return True

        return False

    def _check_trailing_stop(self, code, stock_info, current_price, profit_rate):
        """트레일링 스탑 체크"""
        settings = stock_info['settings']

        if not settings.get('enable_trailing_stop', False):
            return False

        # 최고가 기록
        if code not in self.trailing_high_prices:
            self.trailing_high_prices[code] = current_price
        else:
            self.trailing_high_prices[code] = max(self.trailing_high_prices[code], current_price)

        high_price = self.trailing_high_prices[code]
        trailing_stop_rate = settings.get('trailing_stop_rate', -2.0)

        # 최고가 대비 하락률
        drop_from_high = ((current_price - high_price) / high_price) * 100

        if drop_from_high <= trailing_stop_rate:
            reason = f"트레일링스탑(최고가대비 {drop_from_high:.2f}%)"
            self._execute_sell(code, stock_info, current_price, reason)

            # 최고가 기록 제거
            if code in self.trailing_high_prices:
                del self.trailing_high_prices[code]

            return True

        return False

    def _check_profit_protect(self, code, stock_info, current_price, profit_rate):
        """이익보존 체크"""
        settings = stock_info['settings']

        if not settings.get('enable_profit_protect', False):
            return False

        profit_protect_trigger = settings.get('profit_protect_trigger', 5.0)
        profit_protect_sell = settings.get('profit_protect_sell', 2.0)

        # 이익보존 발동 조건: 일정 수익률 달성 후 하락
        if profit_rate >= profit_protect_trigger:
            # 최고 수익률 기록
            if code not in self.trailing_high_prices:
                self.trailing_high_prices[code] = current_price

            # 현재 수익률이 보존 수익률 이하로 떨어지면 매도
            if profit_rate <= profit_protect_sell:
                reason = f"이익보존({profit_rate:.2f}%)"
                self._execute_sell(code, stock_info, current_price, reason)

                if code in self.trailing_high_prices:
                    del self.trailing_high_prices[code]

                return True

        return False

    def _check_time_exit(self, code, stock_info):
        """시간 청산 체크"""
        settings = stock_info['settings']

        if not settings.get('enable_time_exit', False):
            return False

        exit_hour = settings.get('time_exit_hour', 15)
        exit_minute = settings.get('time_exit_minute', 20)

        from datetime import datetime
        now = datetime.now()

        if now.hour >= exit_hour and now.minute >= exit_minute:
            current_price = self._get_current_price(code)
            reason = f"시간청산({exit_hour}:{exit_minute:02d})"
            self._execute_sell(code, stock_info, current_price, reason)
            return True

        return False

    def _execute_sell(self, code, stock_info, sell_price, reason):
        """매도 실행"""
        name = stock_info['name']
        quantity = stock_info['quantity']
        buy_price = stock_info['buy_price']
        profit_rate = ((sell_price - buy_price) / buy_price) * 100

        print(f"[매도 실행] {name}({code}) {quantity}주 @ {sell_price}원 - {reason}")

        # 주문 전송
        order_type = 2  # 신규 매도
        screen_no = "0102"
        rqname = f"매도_{code}"
        hoga_gb = "03"  # 시장가

        ret = self.api.send_order(
            rqname,
            screen_no,
            self.api.account_number,
            order_type,
            code,
            quantity,
            0,  # 시장가는 0
            hoga_gb,
            ""
        )

        if ret == 0:
            print(f"[매도 주문 성공] {name}({code}) 수익률: {profit_rate:.2f}%")
            self.sell_order_sent.emit(code, quantity, sell_price, reason)
            self.sell_completed.emit(code, quantity, sell_price, profit_rate)

            # 매수 목록에서 제거
            self.buy_strategy.remove_stock(code)

        else:
            print(f"[매도 주문 실패] {name}({code}) - 오류코드: {ret}")

    def _get_current_price(self, code):
        """현재가 조회 (간단 구현)"""
        # 실제로는 실시간 시세를 받아와야 함
        # TODO: 실시간 시세 연동
        return 10000  # 임시값

    def manual_sell(self, code, quantity=None, reason="수동매도"):
        """수동 매도"""
        bought_stocks = self.buy_strategy.get_bought_stocks()

        if code not in bought_stocks:
            print(f"[매도 실패] 보유하지 않은 종목: {code}")
            return False

        stock_info = bought_stocks[code]

        if quantity is None:
            quantity = stock_info['quantity']

        current_price = self._get_current_price(code)
        self._execute_sell(code, stock_info, current_price, reason)

        return True

    def sell_all(self, reason="전체청산"):
        """전체 매도"""
        bought_stocks = self.buy_strategy.get_bought_stocks()

        for code in list(bought_stocks.keys()):
            stock_info = bought_stocks[code]
            current_price = self._get_current_price(code)
            self._execute_sell(code, stock_info, current_price, reason)

        print("[전체 매도 완료]")
