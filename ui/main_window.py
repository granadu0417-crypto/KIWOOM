"""
메인 윈도우 GUI
"""
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLabel, QTableWidget, QTableWidgetItem,
                              QGroupBox, QComboBox, QSpinBox, QDoubleSpinBox,
                              QCheckBox, QLineEdit, QMessageBox, QTabWidget,
                              QHeaderView)
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QColor
import sys


class MainWindow(QMainWindow):
    """메인 윈도우"""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller

        # 윈도우 설정
        self.setWindowTitle("키움증권 자동매매 프로그램")
        self.setGeometry(100, 100, 1400, 900)

        # UI 초기화
        self.init_ui()

        # 시그널 연결
        self.connect_signals()

    def init_ui(self):
        """UI 초기화"""
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)

        # 상단 정보 패널
        main_layout.addWidget(self.create_info_panel())

        # 조건검색 슬롯 패널
        main_layout.addWidget(self.create_condition_slots_panel())

        # 하단 탭 (거래현황, 로그, 설정)
        main_layout.addWidget(self.create_bottom_tabs())

    def create_info_panel(self):
        """상단 정보 패널"""
        group = QGroupBox("계좌 정보")
        layout = QHBoxLayout()

        # 로그인 상태
        self.login_status_label = QLabel("상태: 미연결")
        layout.addWidget(self.login_status_label)

        # 서버 타입 (모의투자/실전투자)
        self.server_type_label = QLabel("서버: -")
        self.server_type_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(self.server_type_label)

        # 계좌 선택
        layout.addWidget(QLabel("계좌:"))
        self.account_combo = QComboBox()
        layout.addWidget(self.account_combo)

        # 예수금
        self.deposit_label = QLabel("예수금: 0원")
        layout.addWidget(self.deposit_label)

        # 실현손익
        self.profit_label = QLabel("실현손익: 0원 (0.00%)")
        self.profit_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(self.profit_label)

        layout.addStretch()

        # 로그인 버튼
        self.login_button = QPushButton("로그인")
        self.login_button.clicked.connect(self.on_login_clicked)
        layout.addWidget(self.login_button)

        # 전체 매도 버튼
        self.sell_all_button = QPushButton("전체 매도")
        self.sell_all_button.clicked.connect(self.on_sell_all_clicked)
        self.sell_all_button.setEnabled(False)
        self.sell_all_button.setStyleSheet("background-color: #ff6b6b;")
        layout.addWidget(self.sell_all_button)

        group.setLayout(layout)
        return group

    def create_condition_slots_panel(self):
        """조건검색 슬롯 패널 (5개)"""
        group = QGroupBox("조건검색 슬롯")
        layout = QVBoxLayout()

        self.condition_widgets = []

        for i in range(5):
            slot_widget = self.create_condition_slot(i)
            self.condition_widgets.append(slot_widget)
            layout.addWidget(slot_widget)

        group.setLayout(layout)
        return group

    def create_condition_slot(self, slot_number):
        """개별 조건검색 슬롯"""
        group = QGroupBox(f"슬롯 {slot_number + 1}")
        layout = QHBoxLayout()

        # 활성화 체크박스
        enabled_check = QCheckBox("사용")
        enabled_check.stateChanged.connect(
            lambda state, num=slot_number: self.on_slot_enabled_changed(num, state)
        )
        layout.addWidget(enabled_check)

        # 조건검색 선택
        layout.addWidget(QLabel("조건:"))
        condition_combo = QComboBox()
        condition_combo.setMinimumWidth(200)
        layout.addWidget(condition_combo)

        # 매수금액
        layout.addWidget(QLabel("매수금액:"))
        buy_amount_spin = QSpinBox()
        buy_amount_spin.setRange(10000, 10000000)
        buy_amount_spin.setValue(100000)
        buy_amount_spin.setSingleStep(10000)
        buy_amount_spin.setSuffix("원")
        layout.addWidget(buy_amount_spin)

        # 익절률
        layout.addWidget(QLabel("익절:"))
        profit_cut_spin = QDoubleSpinBox()
        profit_cut_spin.setRange(0.1, 50.0)
        profit_cut_spin.setValue(5.0)
        profit_cut_spin.setSingleStep(0.5)
        profit_cut_spin.setSuffix("%")
        layout.addWidget(profit_cut_spin)

        # 손절률
        layout.addWidget(QLabel("손절:"))
        loss_cut_spin = QDoubleSpinBox()
        loss_cut_spin.setRange(-50.0, -0.1)
        loss_cut_spin.setValue(-3.0)
        loss_cut_spin.setSingleStep(0.5)
        loss_cut_spin.setSuffix("%")
        layout.addWidget(loss_cut_spin)

        # 시작/중지 버튼
        start_button = QPushButton("시작")
        start_button.clicked.connect(lambda: self.on_start_condition(slot_number))
        start_button.setEnabled(False)
        layout.addWidget(start_button)

        stop_button = QPushButton("중지")
        stop_button.clicked.connect(lambda: self.on_stop_condition(slot_number))
        stop_button.setEnabled(False)
        layout.addWidget(stop_button)

        # 설정 버튼
        settings_button = QPushButton("⚙️")
        settings_button.setMaximumWidth(40)
        settings_button.clicked.connect(lambda: self.on_slot_settings(slot_number))
        layout.addWidget(settings_button)

        layout.addStretch()

        group.setLayout(layout)

        # 위젯 참조 저장
        group.enabled_check = enabled_check
        group.condition_combo = condition_combo
        group.buy_amount_spin = buy_amount_spin
        group.profit_cut_spin = profit_cut_spin
        group.loss_cut_spin = loss_cut_spin
        group.start_button = start_button
        group.stop_button = stop_button

        return group

    def create_bottom_tabs(self):
        """하단 탭"""
        tabs = QTabWidget()

        # 보유종목 탭
        tabs.addTab(self.create_holdings_table(), "보유종목")

        # 조건 편입/이탈 탭
        tabs.addTab(self.create_condition_log_table(), "조건 편입/이탈")

        # 거래내역 탭
        tabs.addTab(self.create_trades_table(), "거래내역")

        # 로그 탭
        tabs.addTab(self.create_log_panel(), "로그")

        return tabs

    def create_condition_log_table(self):
        """조건 편입/이탈 로그 테이블"""
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels([
            "시간", "구분", "조건검색명", "종목명", "종목코드"
        ])

        # 테이블 설정
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)

        # 최신 항목이 위로 오도록 설정
        table.setSortingEnabled(False)

        self.condition_log_table = table
        return table

    def create_holdings_table(self):
        """보유종목 테이블"""
        table = QTableWidget()
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels([
            "종목코드", "종목명", "보유수량", "매수가", "현재가", "수익률", "평가손익", "슬롯"
        ])

        # 테이블 설정
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)

        self.holdings_table = table
        return table

    def create_trades_table(self):
        """거래내역 테이블"""
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels([
            "시간", "구분", "종목명", "수량", "가격", "수익률", "사유"
        ])

        # 테이블 설정
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.trades_table = table
        return table

    def create_log_panel(self):
        """로그 패널"""
        from PyQt5.QtWidgets import QTextEdit

        log_text = QTextEdit()
        log_text.setReadOnly(True)

        self.log_text = log_text
        return log_text

    def connect_signals(self):
        """시그널 연결"""
        pass

    # ===== 이벤트 핸들러 =====

    def on_login_clicked(self):
        """로그인 버튼 클릭"""
        self.controller.login()

    def on_sell_all_clicked(self):
        """전체 매도 버튼 클릭"""
        reply = QMessageBox.question(
            self,
            "전체 매도",
            "모든 보유 종목을 매도하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.controller.sell_all_stocks()

    def on_slot_enabled_changed(self, slot_number, state):
        """슬롯 활성화 변경"""
        enabled = state == Qt.Checked
        widget = self.condition_widgets[slot_number]

        widget.condition_combo.setEnabled(enabled)
        widget.buy_amount_spin.setEnabled(enabled)
        widget.profit_cut_spin.setEnabled(enabled)
        widget.loss_cut_spin.setEnabled(enabled)
        widget.start_button.setEnabled(enabled and self.controller.is_logged_in)

    def on_start_condition(self, slot_number):
        """조건검색 시작"""
        widget = self.condition_widgets[slot_number]
        condition_name = widget.condition_combo.currentText()

        if not condition_name:
            QMessageBox.warning(self, "경고", "조건검색식을 선택하세요.")
            return

        # 설정 가져오기
        settings = {
            'buy_amount': widget.buy_amount_spin.value(),
            'profit_cut_rate': widget.profit_cut_spin.value(),
            'loss_cut_rate': widget.loss_cut_spin.value(),
        }

        self.controller.start_condition_slot(slot_number, condition_name, settings)

        # 버튼 상태 변경
        widget.start_button.setEnabled(False)
        widget.stop_button.setEnabled(True)

    def on_stop_condition(self, slot_number):
        """조건검색 중지"""
        self.controller.stop_condition_slot(slot_number)

        widget = self.condition_widgets[slot_number]
        widget.start_button.setEnabled(True)
        widget.stop_button.setEnabled(False)

    def on_slot_settings(self, slot_number):
        """슬롯 상세 설정"""
        # TODO: 상세 설정 다이얼로그
        QMessageBox.information(self, "설정", f"슬롯 {slot_number + 1} 상세 설정 (개발 중)")

    # ===== UI 업데이트 메서드 =====

    def update_login_status(self, is_logged_in):
        """로그인 상태 업데이트"""
        if is_logged_in:
            self.login_status_label.setText("상태: ✅ 연결됨")
            self.login_status_label.setStyleSheet("color: green;")
            self.login_button.setEnabled(False)
            self.sell_all_button.setEnabled(True)

            # 활성화된 슬롯의 시작 버튼 활성화
            for widget in self.condition_widgets:
                if widget.enabled_check.isChecked():
                    widget.start_button.setEnabled(True)
        else:
            self.login_status_label.setText("상태: ❌ 미연결")
            self.login_status_label.setStyleSheet("color: red;")

    def update_account_list(self, accounts):
        """계좌 목록 업데이트"""
        self.account_combo.clear()
        self.account_combo.addItems(accounts)

    def update_condition_list(self, conditions):
        """조건검색 목록 업데이트"""
        for widget in self.condition_widgets:
            widget.condition_combo.clear()
            widget.condition_combo.addItems(conditions)

    def update_server_type(self, server_type):
        """서버 타입 업데이트 (모의투자/실전투자)"""
        if server_type == "모의투자":
            self.server_type_label.setText(f"서버: ⚠️ {server_type}")
            self.server_type_label.setStyleSheet("font-weight: bold; font-size: 12pt; color: orange;")
        else:
            self.server_type_label.setText(f"서버: 🔴 {server_type}")
            self.server_type_label.setStyleSheet("font-weight: bold; font-size: 12pt; color: red;")

    def update_deposit(self, deposit):
        """예수금 업데이트"""
        self.deposit_label.setText(f"예수금: {deposit:,}원")

    def update_profit(self, profit_amount, profit_rate):
        """실현손익 업데이트"""
        color = "green" if profit_amount >= 0 else "red"
        self.profit_label.setText(f"실현손익: {profit_amount:+,}원 ({profit_rate:+.2f}%)")
        self.profit_label.setStyleSheet(f"font-size: 14pt; font-weight: bold; color: {color};")

    def add_log(self, message):
        """로그 추가"""
        from datetime import datetime
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.append(f"[{timestamp}] {message}")

    def add_condition_log(self, event_type, condition_name, stock_name, stock_code):
        """조건 편입/이탈 로그 추가"""
        from datetime import datetime
        timestamp = datetime.now().strftime('%H:%M:%S')

        # 맨 위에 삽입 (최신 항목이 위로)
        self.condition_log_table.insertRow(0)

        self.condition_log_table.setItem(0, 0, QTableWidgetItem(timestamp))
        self.condition_log_table.setItem(0, 1, QTableWidgetItem(event_type))
        self.condition_log_table.setItem(0, 2, QTableWidgetItem(condition_name))
        self.condition_log_table.setItem(0, 3, QTableWidgetItem(stock_name))
        self.condition_log_table.setItem(0, 4, QTableWidgetItem(stock_code))

        # 색상 설정
        if event_type == "편입":
            color = QColor(200, 255, 200)  # 연한 초록
        else:  # 이탈
            color = QColor(255, 220, 220)  # 연한 빨강

        for col in range(5):
            item = self.condition_log_table.item(0, col)
            if item:
                item.setBackground(color)

    def add_trade_record(self, trade_type, name, quantity, price, profit_rate, reason):
        """거래내역 추가"""
        from datetime import datetime
        timestamp = datetime.now().strftime('%H:%M:%S')

        row = self.trades_table.rowCount()
        self.trades_table.insertRow(row)

        self.trades_table.setItem(row, 0, QTableWidgetItem(timestamp))
        self.trades_table.setItem(row, 1, QTableWidgetItem(trade_type))
        self.trades_table.setItem(row, 2, QTableWidgetItem(name))
        self.trades_table.setItem(row, 3, QTableWidgetItem(str(quantity)))
        self.trades_table.setItem(row, 4, QTableWidgetItem(f"{price:,}"))
        self.trades_table.setItem(row, 5, QTableWidgetItem(f"{profit_rate:+.2f}%"))
        self.trades_table.setItem(row, 6, QTableWidgetItem(reason))

        # 색상 설정
        if trade_type == "매수":
            color = QColor(255, 200, 200)
        else:
            color = QColor(200, 255, 200) if profit_rate >= 0 else QColor(255, 220, 220)

        for col in range(7):
            item = self.trades_table.item(row, col)
            if item:
                item.setBackground(color)

    def update_holdings_table(self, holdings):
        """보유종목 테이블 업데이트"""
        self.holdings_table.setRowCount(0)

        for code, info in holdings.items():
            row = self.holdings_table.rowCount()
            self.holdings_table.insertRow(row)

            # TODO: 현재가 및 수익률 계산
            current_price = 10000  # 임시
            buy_price = info.get('buy_price', 0)
            quantity = info.get('quantity', 0)

            # 매수가가 0이면 수익률 계산 불가
            if buy_price > 0:
                profit_rate = ((current_price - buy_price) / buy_price) * 100
                profit_amount = (current_price - buy_price) * quantity
            else:
                profit_rate = 0.0
                profit_amount = 0

            self.holdings_table.setItem(row, 0, QTableWidgetItem(code))
            self.holdings_table.setItem(row, 1, QTableWidgetItem(info['name']))
            self.holdings_table.setItem(row, 2, QTableWidgetItem(str(quantity)))
            self.holdings_table.setItem(row, 3, QTableWidgetItem(f"{buy_price:,}" if buy_price > 0 else "시장가"))
            self.holdings_table.setItem(row, 4, QTableWidgetItem(f"{current_price:,}"))
            self.holdings_table.setItem(row, 5, QTableWidgetItem(f"{profit_rate:+.2f}%"))
            self.holdings_table.setItem(row, 6, QTableWidgetItem(f"{profit_amount:+,}"))
            self.holdings_table.setItem(row, 7, QTableWidgetItem(str(info['slot_number'])))

            # 수익률에 따른 색상 설정
            color = QColor(200, 255, 200) if profit_rate >= 0 else QColor(255, 200, 200)
            for col in range(8):
                item = self.holdings_table.item(row, col)
                if item:
                    item.setBackground(color)
