"""
키움증권 자동매매 프로그램 - 심플 버전
최소 기능: 로그인, 계좌번호, 서버구분만
"""
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                              QPushButton, QLabel, QMessageBox)
from PyQt5.QtCore import Qt, QObject, pyqtSignal
from kiwoom.kiwoom_api import KiwoomAPI


class SimpleController(QObject):
    """심플 컨트롤러 - 로그인만"""

    login_completed = pyqtSignal(bool)
    account_info = pyqtSignal(str, str)  # 계좌번호, 서버구분

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
                else:
                    print("계좌 정보를 찾을 수 없습니다")
                    self.login_completed.emit(False)
            else:
                print("로그인 실패")
                self.login_completed.emit(False)

        except Exception as e:
            print(f"로그인 오류: {e}")
            self.login_completed.emit(False)


class SimpleWindow(QMainWindow):
    """심플 GUI - 로그인, 계좌번호, 서버구분만 표시"""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller

        # 윈도우 설정
        self.setWindowTitle("키움증권 자동매매 (심플 버전)")
        self.setGeometry(100, 100, 500, 300)

        # UI 초기화
        self.init_ui()

        # 시그널 연결
        self.controller.login_completed.connect(self.on_login_completed)
        self.controller.account_info.connect(self.on_account_info)

    def init_ui(self):
        """UI 초기화"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setSpacing(20)

        # 타이틀
        title = QLabel("키움증권 자동매매 프로그램 (심플 버전)")
        title.setStyleSheet("font-size: 18pt; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 로그인 버튼
        self.login_button = QPushButton("로그인")
        self.login_button.setStyleSheet("font-size: 14pt; padding: 10px;")
        self.login_button.clicked.connect(self.on_login_click)
        layout.addWidget(self.login_button)

        # 로그인 상태 라벨
        self.status_label = QLabel("로그인이 필요합니다")
        self.status_label.setStyleSheet("font-size: 12pt; color: gray;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # 계좌번호 라벨
        self.account_label = QLabel("계좌번호: -")
        self.account_label.setStyleSheet("font-size: 14pt;")
        self.account_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.account_label)

        # 서버 구분 라벨
        self.server_label = QLabel("서버: -")
        self.server_label.setStyleSheet("font-size: 14pt;")
        self.server_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.server_label)

        layout.addStretch()

    def on_login_click(self):
        """로그인 버튼 클릭"""
        self.login_button.setEnabled(False)
        self.status_label.setText("로그인 중...")
        self.controller.login()

    def on_login_completed(self, success):
        """로그인 완료"""
        if success:
            self.status_label.setText("✓ 로그인 성공")
            self.status_label.setStyleSheet("font-size: 12pt; color: green; font-weight: bold;")
            self.login_button.setText("로그인 완료")
        else:
            self.status_label.setText("✗ 로그인 실패")
            self.status_label.setStyleSheet("font-size: 12pt; color: red;")
            self.login_button.setEnabled(True)
            QMessageBox.warning(self, "로그인 실패", "로그인에 실패했습니다.")

    def on_account_info(self, account_no, server_type):
        """계좌 정보 표시"""
        self.account_label.setText(f"계좌번호: {account_no}")

        if server_type == "모의투자":
            self.server_label.setText(f"서버: {server_type} ⚠️")
            self.server_label.setStyleSheet("font-size: 14pt; color: orange; font-weight: bold;")
        else:
            self.server_label.setText(f"서버: {server_type} 🔴")
            self.server_label.setStyleSheet("font-size: 14pt; color: red; font-weight: bold;")


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
    print("  기능: 로그인, 계좌번호, 서버구분만 표시")
    print("=" * 60)
    print()

    app = SimpleApp()
    app.run()


if __name__ == "__main__":
    main()
