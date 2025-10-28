"""
로깅 유틸리티
"""
import logging
import os
from datetime import datetime


def setup_logger(name, log_file, level=logging.INFO):
    """로거 설정"""
    # 로그 디렉토리 생성
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 핸들러가 이미 있으면 제거
    if logger.handlers:
        logger.handlers.clear()

    # 파일 핸들러
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # 포맷터
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


class TradingLogger:
    """트레이딩 전용 로거"""

    def __init__(self, log_dir='logs'):
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 날짜별 로그 파일
        today = datetime.now().strftime('%Y%m%d')
        self.trade_log_file = os.path.join(log_dir, f'trade_{today}.log')
        self.order_log_file = os.path.join(log_dir, f'order_{today}.log')
        self.error_log_file = os.path.join(log_dir, f'error_{today}.log')

        # 로거 생성
        self.trade_logger = setup_logger('trade', self.trade_log_file)
        self.order_logger = setup_logger('order', self.order_log_file)
        self.error_logger = setup_logger('error', self.error_log_file, logging.ERROR)

    def log_trade(self, action, code, name, quantity, price, reason=''):
        """거래 로그"""
        msg = f"{action} | {name}({code}) | {quantity}주 @ {price}원"
        if reason:
            msg += f" | {reason}"
        self.trade_logger.info(msg)

    def log_order(self, order_type, code, name, quantity, price, result):
        """주문 로그"""
        msg = f"{order_type} | {name}({code}) | {quantity}주 @ {price}원 | 결과: {result}"
        self.order_logger.info(msg)

    def log_error(self, error_type, message):
        """에러 로그"""
        self.error_logger.error(f"{error_type} | {message}")

    def log_profit(self, code, name, buy_price, sell_price, quantity, profit_rate):
        """수익 로그"""
        profit_amount = (sell_price - buy_price) * quantity
        msg = f"수익실현 | {name}({code}) | {quantity}주 | " \
              f"매수: {buy_price}원 | 매도: {sell_price}원 | " \
              f"수익률: {profit_rate:.2f}% | 수익금: {profit_amount:,}원"
        self.trade_logger.info(msg)
