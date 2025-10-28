"""
키움증권 자동매매 프로그램 - 심플 버전
기능: 로그인, 계좌번호, 서버구분, 예수금 조회
"""
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLabel, QMessageBox, QGroupBox, QGridLayout)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QTimer
from kiwoom.kiwoom_api import KiwoomAPI


class SimpleController(QObject):
    """심플 컨트롤러"""

    login_completed = pyqtSignal(bool)
    account_info = pyqtSignal(str, str)  # 계좌번호, 서버구분
    deposit_updated = pyqtSignal(int)     # 예수금
    deposit_error = pyqtSignal(str)       # 예수금 조회 오류

    def __init__(self):
        super().__init__()
        self.api = KiwoomAPI()
        self.is_logged_in = False

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
                        server_type = "모의투자"
                    else:
                        server_type = "실전투자"

                    print(f"계좌번호: {account_no}")
                    print(f"서버구분: {server_type}")

                    self.account_info.emit(account_no, server_type)
                    self.login_completed.emit(True)

                    # 로그인 후 예수금 조회
                    self.refresh_deposit()
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

        # 주기적 예수금 갱신 타이머 (30초마다)
        self.deposit_timer = QTimer()
        self.deposit_timer.timeout.connect(self.on_timer_refresh)
        self.deposit_timer.setInterval(30000)  # 30초

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

        info_layout.setColumnStretch(1, 1)
        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)

        # === 하단: 빈 공간 (나중에 채울 예정) ===
        bottom_group = QGroupBox("기능 영역 (준비 중)")
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
        empty_label = QLabel("이 영역은 나중에 기능이 추가될 예정입니다")
        empty_label.setAlignment(Qt.AlignCenter)
        empty_label.setStyleSheet("font-size: 12pt; color: #95a5a6;")
        bottom_layout.addWidget(empty_label)
        bottom_layout.addStretch()

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
        self.controller.refresh_deposit()

    def on_timer_refresh(self):
        """타이머에 의한 자동 갱신"""
        print("[타이머] 예수금 자동 갱신")
        self.controller.refresh_deposit()


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
