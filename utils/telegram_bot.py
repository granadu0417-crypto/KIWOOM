"""
텔레그램 알림 봇
"""
import requests
from datetime import datetime


class TelegramBot:
    """텔레그램 봇 클래스"""

    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{token}"
        self.enabled = bool(token and chat_id)

    def send_message(self, message):
        """메시지 전송"""
        if not self.enabled:
            return False

        try:
            url = f"{self.api_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, data=data, timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"[텔레그램 전송 실패] {e}")
            return False

    def send_buy_notification(self, code, name, quantity, price, slot_number):
        """매수 알림"""
        now = datetime.now().strftime('%H:%M:%S')
        message = f"""
<b>📈 매수 알림</b>
시간: {now}
종목: {name} ({code})
수량: {quantity}주
가격: {price:,}원
슬롯: {slot_number}
        """.strip()
        return self.send_message(message)

    def send_sell_notification(self, code, name, quantity, price, profit_rate, reason):
        """매도 알림"""
        now = datetime.now().strftime('%H:%M:%S')

        # 수익률에 따라 이모지 변경
        if profit_rate > 0:
            emoji = "💰"
            status = "익절"
        elif profit_rate < 0:
            emoji = "📉"
            status = "손절"
        else:
            emoji = "➡️"
            status = "동일가"

        message = f"""
<b>{emoji} 매도 알림 ({status})</b>
시간: {now}
종목: {name} ({code})
수량: {quantity}주
가격: {price:,}원
수익률: {profit_rate:+.2f}%
사유: {reason}
        """.strip()
        return self.send_message(message)

    def send_condition_notification(self, condition_name, code, name, event_type):
        """조건검색 알림"""
        now = datetime.now().strftime('%H:%M:%S')

        if event_type == 'I':
            emoji = "🔔"
            event = "편입"
        else:
            emoji = "🔕"
            event = "이탈"

        message = f"""
<b>{emoji} 조건검색 {event}</b>
시간: {now}
조건: {condition_name}
종목: {name} ({code})
        """.strip()
        return self.send_message(message)

    def send_daily_summary(self, total_trades, profit_count, loss_count, total_profit_rate, total_profit_amount):
        """일일 요약"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        message = f"""
<b>📊 일일 거래 요약</b>
시간: {now}
━━━━━━━━━━━━━━━━
총 거래: {total_trades}건
익절: {profit_count}건
손절: {loss_count}건
━━━━━━━━━━━━━━━━
총 수익률: {total_profit_rate:+.2f}%
총 수익금: {total_profit_amount:+,}원
        """.strip()
        return self.send_message(message)

    def send_error_notification(self, error_type, error_message):
        """에러 알림"""
        now = datetime.now().strftime('%H:%M:%S')

        message = f"""
<b>⚠️ 에러 발생</b>
시간: {now}
유형: {error_type}
내용: {error_message}
        """.strip()
        return self.send_message(message)

    def test_connection(self):
        """연결 테스트"""
        message = "🤖 키움 자동매매 프로그램 연결 테스트"
        return self.send_message(message)
