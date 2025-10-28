"""
키움증권 자동매매 프로그램 - 메인 실행 파일
"""
import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow
from trading.trading_controller import TradingController


class AutoTradingApp:
    """자동매매 애플리케이션"""

    def __init__(self):
        # QApplication 생성
        self.app = QApplication(sys.argv)

        # 컨트롤러 생성
        self.controller = TradingController()

        # 메인 윈도우 생성
        self.main_window = MainWindow(self.controller)

        # 시그널 연결
        self.connect_signals()

    def connect_signals(self):
        """컨트롤러와 GUI 시그널 연결"""
        # 로그인 완료
        self.controller.login_completed.connect(self.main_window.update_login_status)

        # 계좌 업데이트
        self.controller.account_updated.connect(self.main_window.update_account_list)

        # 조건검색 목록 업데이트
        self.controller.condition_list_updated.connect(self.main_window.update_condition_list)

        # 예수금 업데이트
        self.controller.deposit_updated.connect(self.main_window.update_deposit)

        # 로그 메시지
        self.controller.log_message.connect(self.main_window.add_log)

        # 매수 주문
        self.controller.buy_strategy.buy_order_sent.connect(
            lambda code, qty, price, hoga: self.on_buy_order(code, qty, price)
        )

        # 매도 주문
        self.controller.sell_strategy.sell_order_sent.connect(
            lambda code, qty, price, reason: self.on_sell_order(code, qty, price, reason)
        )

        # 매도 체결
        self.controller.sell_strategy.sell_completed.connect(self.on_sell_completed)

    def on_buy_order(self, code, quantity, price):
        """매수 주문 시"""
        stock_name = self.controller.api.get_master_code_name(code)
        self.main_window.add_trade_record("매수", stock_name, quantity, price, 0.0, "신규매수")

        # 보유종목 테이블 업데이트
        self.update_holdings_table()

    def on_sell_order(self, code, quantity, price, reason):
        """매도 주문 시"""
        pass

    def on_sell_completed(self, code, quantity, sell_price, profit_rate):
        """매도 체결 시"""
        stock_name = self.controller.api.get_master_code_name(code)
        self.main_window.add_trade_record("매도", stock_name, quantity, sell_price, profit_rate, "")

        # 보유종목 테이블 업데이트
        self.update_holdings_table()

    def update_holdings_table(self):
        """보유종목 테이블 업데이트"""
        holdings = self.controller.get_bought_stocks()
        self.main_window.update_holdings_table(holdings)

    def run(self):
        """애플리케이션 실행"""
        self.main_window.show()
        sys.exit(self.app.exec_())


def main():
    """메인 함수"""
    print("=" * 60)
    print("  키움증권 자동매매 프로그램")
    print("=" * 60)
    print()
    print("주의사항:")
    print("1. 이 프로그램은 Windows 환경에서만 실행됩니다.")
    print("2. 키움증권 OpenAPI+가 설치되어 있어야 합니다.")
    print("3. 반드시 모의투자 계좌로 먼저 테스트하세요.")
    print("4. 투자 손실의 책임은 사용자에게 있습니다.")
    print()
    print("=" * 60)
    print()

    # 애플리케이션 실행
    app = AutoTradingApp()
    app.run()


if __name__ == "__main__":
    main()
