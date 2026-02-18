import os
import pandas as pd
import simfin as sf
import finnhub
import yfinance as yf
from telegram import Bot
import asyncio
from datetime import datetime

# Config
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
FINNHUB_KEY = os.getenv('FINNHUB_API_KEY')

# SimFin 초기화
sf.set_api_key(api_key=os.getenv('SIMFIN_API_KEY'))

async def send_telegram_message(bot, text):
    await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode='Markdown')

def get_value_stocks():
    # US 대형주 로드
    df = sf.load_dataset(version='v4', variant='fundamental', endpoint='shares', market='us')
    
    # 버핏 스타일 필터링 (예시 기준, 필요 시 조정 가능)
    df = df[
        (df['marketcap'] > 10e9) &        # 시총 > 100억 달러
        (df['roe'] > 0.15) &             # ROE > 15%
        (df['debt2equity'] < 0.5) &      # D/E < 0.5
        (df['pe'] < 15)                  # PER < 15
    ]
    
    # 점수 계산 (예: 중요도 ROE 40%, PER 40%, D/E 20%)
    df['score'] = (
        df['roe'] * 0.4 +
        (1 / (df['pe'] + 0.1)) * 0.4 +
        (1 / (df['debt2equity'] + 0.1)) * 0.2
    )
    
    top10 = df.nlargest(10, 'score')[['ticker', 'score', 'price', 'pe', 'roe']].round(2)
    top10.columns = ['종목', '점수', '현재가', 'PER', 'ROE']
    
    return top10.to_markdown(index=False, tablefmt='simple')

def tqqq_signal():
    # TQQQ 최근 1개월 데이터
    tqqq = yf.Ticker('TQQQ')
    hist = tqqq.history(period='1mo')
    
    current_price = hist['Close'][-1]
    avg_price = hist['Close'].mean()
    
    # 무한매수 신호: 10% 상승 시 매도, 평단 대비 5% 이하 시 매수
    if current_price > avg_price * 1.1:
        signal = '매도 신호 (10% 상승)'
    elif current_price < avg_price * 0.95:
        signal = '매수 신호 (5% 이하)'
    else:
        signal = '관망'

    return f"""
TQQQ 무한매수 상태 (실험용)
• 평단가: {avg_price:.2f}$
• 현재가: {current_price:.2f}$
• 신호: {signal}
"""

async def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    
    try:
        value_table = get_value_stocks()
        tqqq_block = tqqq_signal()
        
        message = f"""📊 *주간 가치투자 스크리너 결과* ({datetime.now().strftime('%Y-%m-%d')})

