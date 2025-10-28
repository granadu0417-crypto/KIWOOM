"""
키움증권 자동매매 프로그램 - 심플 버전
기능: 로그인, 계좌번호, 서버구분, 예수금 조회
"""
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLabel, QMessageBox, QGroupBox, QGridLayout, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QTimer
from kiwoom.kiwoom_api import KiwoomAPI


class SimpleController(QObject):
    """심플 컨트롤러"""

    login_completed = pyqtSignal(bool)
    account_info = pyqtSignal(str, str)  # 계좌번호, 서버구분
    deposit_updated = pyqtSignal(int)     # 예수금
    deposit_error = pyqtSignal(str)       # 예수금 조회 오류
    stats_updated = pyqtSignal(int, int, int, float)  # 총매입, 총평가, 총손익, 총수익률
    holdings_table_updated = pyqtSignal(dict)  # 보유종목 테이블 업데이트

    def __init__(self):
        super().__init__()
        self.api = KiwoomAPI()
        self.is_logged_in = False
        self.server_type = "모의투자"  # 기본값
        self.holdings = {}  # 보유종목 {종목코드: {name, quantity, buy_price, current_price}}

    def login(self):
        """로그인"""
        try:
            print("로그인 시도 중...")
            self.api.comm_connect()

            if self.api.is_connected:
                self.is_logged_in = True
                print("로그인 성공!")

                # 계좌 정보 가져오기
                accounts = self.api.get_account_list()
                if accounts:
                    account_no = accounts[0]
                    self.api.set_account_number(account_no)

                    # 서버 구분
                    server_gubun = self.api.get_server_gubun()
                    if server_gubun == "1":
                        self.server_type = "모의투자"
                    else:
                        self.server_type = "실전투자"

                    print(f"계좌번호: {account_no}")
                    print(f"서버구분: {self.server_type}")

                    self.account_info.emit(account_no, self.server_type)
                    self.login_completed.emit(True)

                    # 로그인 후 예수금 조회
                    self.refresh_deposit()

                    # 로그인 후 보유종목 조회
                    self.refresh_holdings()
                else:
                    print("계좌 정보를 찾을 수 없습니다")
                    self.login_completed.emit(False)
            else:
                print("로그인 실패")
                self.login_completed.emit(False)

        except Exception as e:
            print(f"로그인 오류: {e}")
            self.login_completed.emit(False)

    def refresh_deposit(self):
        """예수금 조회"""
        if not self.is_logged_in:
            return

        try:
            print("예수금 조회 중...")
            deposit = self.api.request_deposit()
            print(f"예수금: {deposit:,}원")
            self.deposit_updated.emit(deposit)
        except Exception as e:
            error_msg = f"예수금 조회 실패: {e}"
            print(error_msg)
            self.deposit_error.emit(error_msg)

    def refresh_holdings(self):
        """보유종목 조회 (1단계)"""
        if not self.is_logged_in:
            return

        try:
            print("보유종목 조회 중...")
            self.holdings = self.api.request_balance()
            print(f"보유종목: {len(self.holdings)}개")

            # 보유종목 상세 출력
            for code, info in self.holdings.items():
                print(f"  - {info['name']}({code}): {info['quantity']}주 @ {info['buy_price']:,}원")

            # 실시간 시세 등록 (3단계)
            self.register_real_prices()

            # 통계 계산 및 업데이트 (2단계)
            self.calculate_and_update_stats()

        except Exception as e:
            error_msg = f"보유종목 조회 실패: {e}"
            print(error_msg)

    def register_real_prices(self):
        """보유종목 실시간 시세 등록 (3단계)"""
        if not self.holdings:
            return

        # 모든 보유종목의 종목코드 리스트
        code_list = ";".join(self.holdings.keys())

        # 실시간 등록 (FID: 10=현재가, 12=등락률, 13=누적거래량)
        fid_list = "10;12;13"
        screen_no = "1000"

        try:
            self.api.set_real_reg(screen_no, code_list, fid_list, "0")  # "0"=기존 제거 후 등록
            print(f"[실시간] {len(self.holdings)}개 종목 실시간 시세 등록 완료")
        except Exception as e:
            print(f"[실시간] 시세 등록 실패: {e}")

    def update_realtime_prices(self):
        """실시간 시세 업데이트 (3단계)"""
        if not self.holdings:
            return

        # API의 real_data에서 현재가 가져와서 holdings 업데이트
        updated = False
        for code in self.holdings.keys():
            if code in self.api.real_data:
                real_price = self.api.real_data[code].get('current_price', 0)
                if real_price > 0:
                    self.holdings[code]['current_price'] = real_price
                    updated = True

        # 업데이트 되었으면 통계 재계산
        if updated:
            self.calculate_and_update_stats()

    def calculate_and_update_stats(self):
        """통계 계산 및 업데이트 (2단계) - 수수료/세금 반영"""
        if not self.holdings:
            # 보유종목 없으면 모두 0
            self.stats_updated.emit(0, 0, 0, 0.0)
            return

        total_buy = 0      # 총매입
        total_eval = 0     # 총평가
        total_profit = 0   # 총손익 (수수료/세금 포함)

        for code, info in self.holdings.items():
            buy_price = info.get('buy_price', 0)
            quantity = info.get('quantity', 0)
            current_price = info.get('current_price', buy_price)  # 실시간 전에는 매입가 사용

            total_buy += buy_price * quantity
            total_eval += current_price * quantity

            # 각 종목의 평가손익 계산 (수수료/세금 포함)
            profit, _ = self.calculate_profit_with_fees(buy_price, current_price, quantity)
            total_profit += profit

        total_profit_rate = (total_profit / total_buy * 100) if total_buy > 0 else 0.0  # 총수익률

        print(f"[통계] 총매입: {total_buy:,}원 / 총평가: {total_eval:,}원 / 총손익: {total_profit:+,}원 / 총수익률: {total_profit_rate:+.2f}%")

        self.stats_updated.emit(total_buy, total_eval, total_profit, total_profit_rate)
        self.holdings_table_updated.emit(self.holdings)  # 보유종목 테이블도 업데이트

    def calculate_profit_with_fees(self, buy_price, current_price, quantity):
        """
        수수료와 세금을 고려한 평가손익 계산

        Args:
            buy_price: 매입가 (이미 매수수수료 포함)
            current_price: 현재가
            quantity: 수량

        Returns:
            (평가손익, 수익률)
        """
        buy_amount = buy_price * quantity  # 매수금액 (수수료 포함)
        eval_amount = current_price * quantity  # 평가금액

        # 실전투자일 경우 매도 시 발생할 수수료와 세금 차감
        if self.server_type == "실전투자":
            # 매도 수수료 (일반적으로 0.015%)
            sell_fee = eval_amount * 0.00015
            # 증권거래세 (0.23%)
            tax = eval_amount * 0.0023

            # 평가손익 = 평가금액 - 매수금액 - 매도수수료 - 세금
            profit = eval_amount - buy_amount - sell_fee - tax
        else:
            # 모의투자는 수수료/세금 없음
            profit = eval_amount - buy_amount

        # 수익률
        profit_rate = (profit / buy_amount * 100) if buy_amount > 0 else 0.0

        return profit, profit_rate


class SimpleWindow(QMainWindow):
    """심플 GUI"""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller

        # 윈도우 설정
        self.setWindowTitle("키움증권 자동매매 프로그램 (심플 버전)")
        self.setGeometry(100, 100, 1200, 800)

        # UI 초기화
        self.init_ui()

        # 시그널 연결
        self.controller.login_completed.connect(self.on_login_completed)
        self.controller.account_info.connect(self.on_account_info)
        self.controller.deposit_updated.connect(self.on_deposit_updated)
        self.controller.deposit_error.connect(self.on_deposit_error)
        self.controller.stats_updated.connect(self.on_stats_updated)
        self.controller.holdings_table_updated.connect(self.on_holdings_table_updated)

        # 주기적 예수금 갱신 타이머 (30초마다)
        self.deposit_timer = QTimer()
        self.deposit_timer.timeout.connect(self.on_timer_refresh)
        self.deposit_timer.setInterval(30000)  # 30초

        # 실시간 가격 업데이트 타이머 (1초마다)
        self.realtime_timer = QTimer()
        self.realtime_timer.timeout.connect(self.on_realtime_update)
        self.realtime_timer.setInterval(1000)  # 1초

    def init_ui(self):
        """UI 초기화"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # === 상단: 타이틀 + 로그인 버튼 ===
        top_layout = QHBoxLayout()

        # 타이틀
        title = QLabel("키움증권 자동매매 프로그램")
        title.setStyleSheet("font-size: 20pt; font-weight: bold; color: #2c3e50;")
        top_layout.addWidget(title)

        top_layout.addStretch()

        # 로그인 버튼
        self.login_button = QPushButton("로그인")
        self.login_button.setStyleSheet("""
            QPushButton {
                font-size: 14pt;
                padding: 10px 30px;
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.login_button.clicked.connect(self.on_login_click)
        top_layout.addWidget(self.login_button)

        main_layout.addLayout(top_layout)

        # === 계좌 정보 패널 ===
        info_group = QGroupBox("계좌 정보")
        info_group.setStyleSheet("""
            QGroupBox {
                font-size: 14pt;
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
            }
        """)

        info_layout = QGridLayout()
        info_layout.setSpacing(15)
        info_layout.setContentsMargins(20, 20, 20, 20)

        # === 좌측 열 ===
        # 로그인 상태
        status_label_title = QLabel("로그인 상태:")
        status_label_title.setStyleSheet("font-size: 13pt; font-weight: bold;")
        self.status_label = QLabel("로그인이 필요합니다")
        self.status_label.setStyleSheet("font-size: 13pt; color: #7f8c8d;")
        info_layout.addWidget(status_label_title, 0, 0)
        info_layout.addWidget(self.status_label, 0, 1)

        # 계좌번호
        account_label_title = QLabel("계좌번호:")
        account_label_title.setStyleSheet("font-size: 13pt; font-weight: bold;")
        self.account_label = QLabel("-")
        self.account_label.setStyleSheet("font-size: 13pt;")
        info_layout.addWidget(account_label_title, 1, 0)
        info_layout.addWidget(self.account_label, 1, 1)

        # 서버 구분
        server_label_title = QLabel("서버 구분:")
        server_label_title.setStyleSheet("font-size: 13pt; font-weight: bold;")
        self.server_label = QLabel("-")
        self.server_label.setStyleSheet("font-size: 13pt;")
        info_layout.addWidget(server_label_title, 2, 0)
        info_layout.addWidget(self.server_label, 2, 1)

        # 예수금
        deposit_label_title = QLabel("예수금:")
        deposit_label_title.setStyleSheet("font-size: 13pt; font-weight: bold;")

        deposit_h_layout = QHBoxLayout()
        self.deposit_label = QLabel("-")
        self.deposit_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #27ae60;")
        deposit_h_layout.addWidget(self.deposit_label)

        # 새로고침 버튼
        self.refresh_button = QPushButton("🔄 새로고침")
        self.refresh_button.setStyleSheet("""
            QPushButton {
                font-size: 11pt;
                padding: 5px 15px;
                background-color: #16a085;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1abc9c;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.refresh_button.clicked.connect(self.on_refresh_click)
        self.refresh_button.setEnabled(False)
        deposit_h_layout.addWidget(self.refresh_button)
        deposit_h_layout.addStretch()

        info_layout.addWidget(deposit_label_title, 3, 0)
        info_layout.addLayout(deposit_h_layout, 3, 1)

        # === 우측 열 (통계) ===
        # 총매입
        total_buy_title = QLabel("총매입:")
        total_buy_title.setStyleSheet("font-size: 13pt; font-weight: bold;")
        self.total_buy_label = QLabel("0원")
        self.total_buy_label.setStyleSheet("font-size: 13pt;")
        info_layout.addWidget(total_buy_title, 0, 2)
        info_layout.addWidget(self.total_buy_label, 0, 3)

        # 총평가
        total_eval_title = QLabel("총평가:")
        total_eval_title.setStyleSheet("font-size: 13pt; font-weight: bold;")
        self.total_eval_label = QLabel("0원")
        self.total_eval_label.setStyleSheet("font-size: 13pt;")
        info_layout.addWidget(total_eval_title, 1, 2)
        info_layout.addWidget(self.total_eval_label, 1, 3)

        # 총손익
        total_profit_title = QLabel("총손익:")
        total_profit_title.setStyleSheet("font-size: 13pt; font-weight: bold;")
        self.total_profit_label = QLabel("0원")
        self.total_profit_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #7f8c8d;")
        info_layout.addWidget(total_profit_title, 2, 2)
        info_layout.addWidget(self.total_profit_label, 2, 3)

        # 총수익률
        total_profit_rate_title = QLabel("총수익률:")
        total_profit_rate_title.setStyleSheet("font-size: 13pt; font-weight: bold;")
        self.total_profit_rate_label = QLabel("0.00%")
        self.total_profit_rate_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #7f8c8d;")
        info_layout.addWidget(total_profit_rate_title, 3, 2)
        info_layout.addWidget(self.total_profit_rate_label, 3, 3)

        info_layout.setColumnStretch(1, 1)
        info_layout.setColumnStretch(3, 1)
        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)

        # === 하단: 보유종목 테이블 ===
        bottom_group = QGroupBox("보유종목")
        bottom_group.setStyleSheet("""
            QGroupBox {
                font-size: 14pt;
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
            }
        """)

        bottom_layout = QVBoxLayout()

        # 보유종목 테이블
        self.holdings_table = QTableWidget()
        self.holdings_table.setColumnCount(7)
        self.holdings_table.setHorizontalHeaderLabels(["종목코드", "종목명", "수량", "매입가", "현재가", "평가손익", "수익률"])

        # 테이블 스타일
        self.holdings_table.setStyleSheet("""
            QTableWidget {
                font-size: 11pt;
                gridline-color: #bdc3c7;
                background-color: white;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 8px;
                font-weight: bold;
                font-size: 12pt;
            }
        """)

        # 헤더 설정
        header = self.holdings_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 종목코드
        header.setSectionResizeMode(1, QHeaderView.Stretch)           # 종목명
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 수량
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 매입가
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 현재가
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # 평가손익
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # 수익률

        self.holdings_table.verticalHeader().setVisible(False)
        self.holdings_table.setAlternatingRowColors(True)
        self.holdings_table.setSelectionBehavior(QTableWidget.SelectRows)

        bottom_layout.addWidget(self.holdings_table)
        bottom_group.setLayout(bottom_layout)
        main_layout.addWidget(bottom_group)

    def on_login_click(self):
        """로그인 버튼 클릭"""
        self.login_button.setEnabled(False)
        self.status_label.setText("로그인 중...")
        self.status_label.setStyleSheet("font-size: 13pt; color: #f39c12;")
        self.controller.login()

    def on_login_completed(self, success):
        """로그인 완료"""
        if success:
            self.status_label.setText("✓ 로그인 성공")
            self.status_label.setStyleSheet("font-size: 13pt; color: #27ae60; font-weight: bold;")
            self.login_button.setText("로그인 완료")
            self.refresh_button.setEnabled(True)

            # 주기적 갱신 시작
            self.deposit_timer.start()
            self.realtime_timer.start()  # 실시간 가격 업데이트 시작
        else:
            self.status_label.setText("✗ 로그인 실패")
            self.status_label.setStyleSheet("font-size: 13pt; color: #e74c3c;")
            self.login_button.setEnabled(True)
            QMessageBox.warning(self, "로그인 실패", "로그인에 실패했습니다.")

    def on_account_info(self, account_no, server_type):
        """계좌 정보 표시"""
        self.account_label.setText(account_no)

        if server_type == "모의투자":
            self.server_label.setText(f"{server_type} ⚠️")
            self.server_label.setStyleSheet("font-size: 13pt; color: #f39c12; font-weight: bold;")
        else:
            self.server_label.setText(f"{server_type} 🔴")
            self.server_label.setStyleSheet("font-size: 13pt; color: #e74c3c; font-weight: bold;")

    def on_deposit_updated(self, deposit):
        """예수금 업데이트"""
        self.deposit_label.setText(f"{deposit:,}원")

    def on_deposit_error(self, error_msg):
        """예수금 조회 오류"""
        self.deposit_label.setText("조회 실패")
        self.deposit_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #e74c3c;")
        QMessageBox.warning(self, "예수금 조회 오류", error_msg)

    def on_refresh_click(self):
        """새로고침 버튼 클릭"""
        print("[새로고침] 예수금 및 보유종목 갱신")
        self.controller.refresh_deposit()
        self.controller.refresh_holdings()

    def on_timer_refresh(self):
        """타이머에 의한 자동 갱신"""
        print("[타이머] 예수금 및 보유종목 자동 갱신")
        self.controller.refresh_deposit()
        self.controller.refresh_holdings()

    def on_stats_updated(self, total_buy, total_eval, total_profit, total_profit_rate):
        """통계 업데이트 (2단계)"""
        # 총매입
        self.total_buy_label.setText(f"{total_buy:,}원")

        # 총평가
        self.total_eval_label.setText(f"{total_eval:,}원")

        # 총손익 (색상 변경)
        if total_profit > 0:
            color = "#e74c3c"  # 빨강 (수익)
            sign = "+"
        elif total_profit < 0:
            color = "#3498db"  # 파랑 (손실)
            sign = ""
        else:
            color = "#7f8c8d"  # 회색 (0)
            sign = ""

        self.total_profit_label.setText(f"{sign}{total_profit:,}원")
        self.total_profit_label.setStyleSheet(f"font-size: 16pt; font-weight: bold; color: {color};")

        # 총수익률 (색상 변경)
        if total_profit_rate > 0:
            color = "#e74c3c"  # 빨강
            sign = "+"
        elif total_profit_rate < 0:
            color = "#3498db"  # 파랑
            sign = ""
        else:
            color = "#7f8c8d"  # 회색
            sign = ""

        self.total_profit_rate_label.setText(f"{sign}{total_profit_rate:.2f}%")
        self.total_profit_rate_label.setStyleSheet(f"font-size: 16pt; font-weight: bold; color: {color};")

    def on_realtime_update(self):
        """실시간 가격 업데이트 (1초마다)"""
        self.controller.update_realtime_prices()

    def on_holdings_table_updated(self, holdings):
        """보유종목 테이블 업데이트"""
        # 테이블 초기화
        self.holdings_table.setRowCount(0)

        if not holdings:
            return

        # 보유종목 데이터 추가
        self.holdings_table.setRowCount(len(holdings))

        for row, (code, info) in enumerate(holdings.items()):
            # 종목코드
            item = QTableWidgetItem(code)
            item.setTextAlignment(Qt.AlignCenter)
            self.holdings_table.setItem(row, 0, item)

            # 종목명
            item = QTableWidgetItem(info.get('name', '-'))
            self.holdings_table.setItem(row, 1, item)

            # 수량
            quantity = info.get('quantity', 0)
            item = QTableWidgetItem(f"{quantity:,}")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.holdings_table.setItem(row, 2, item)

            # 매입가
            buy_price = info.get('buy_price', 0)
            item = QTableWidgetItem(f"{buy_price:,}원")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.holdings_table.setItem(row, 3, item)

            # 현재가
            current_price = info.get('current_price', buy_price)
            item = QTableWidgetItem(f"{current_price:,}원")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.holdings_table.setItem(row, 4, item)

            # 평가손익 및 수익률 (수수료/세금 반영)
            eval_profit, profit_rate = self.controller.calculate_profit_with_fees(buy_price, current_price, quantity)

            # 평가손익
            item = QTableWidgetItem(f"{int(eval_profit):+,}원")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            # 색상 지정
            if eval_profit > 0:
                item.setForeground(Qt.red)
            elif eval_profit < 0:
                item.setForeground(Qt.blue)

            self.holdings_table.setItem(row, 5, item)

            # 수익률
            item = QTableWidgetItem(f"{profit_rate:+.2f}%")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            # 색상 지정
            if profit_rate > 0:
                item.setForeground(Qt.red)
            elif profit_rate < 0:
                item.setForeground(Qt.blue)

            self.holdings_table.setItem(row, 6, item)


class SimpleApp:
    """심플 앱"""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.controller = SimpleController()
        self.window = SimpleWindow(self.controller)

    def run(self):
        """실행"""
        self.window.show()
        sys.exit(self.app.exec_())


def main():
    """메인 함수"""
    print("=" * 60)
    print("  키움증권 자동매매 프로그램 (심플 버전)")
    print("  기능: 로그인, 계좌번호, 서버구분, 예수금 조회")
    print("=" * 60)
    print()

    app = SimpleApp()
    app.run()


if __name__ == "__main__":
    main()
