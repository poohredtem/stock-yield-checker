import os
import pandas as pd
import yfinance as ticker
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, PushMessageRequest, TextMessage

def main():
    # --- Configuration from Environment Variables ---
    CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    USER_ID = os.getenv('LINE_USER_ID')
    CSV_FILE = './assetbalance(JP)_20260220_201541.csv'
    TARGET_YIELD = 3.5

    if not CHANNEL_ACCESS_TOKEN or not USER_ID:
        print('Error: LINE_CHANNEL_ACCESS_TOKEN or LINE_USER_ID environment variables are not set.')
        return

    # --- 1. Extract stock codes from CSV ---
    try:
        df = pd.read_csv(CSV_FILE, encoding='shift_jis', skiprows=6, on_bad_lines='skip')
        codes = [str(code) + '.T' for code in df['銘柄コード'].unique() if str(code).isdigit()]
    except Exception as e:
        print(f'CSV reading error: {e}')
        codes = []

    # --- 2. Yield Check Logic ---
    buy_signals = []
    for symbol in codes:
        try:
            stock = ticker.Ticker(symbol)
            latest_price = stock.history(period='1d')['Close'].iloc[-1]
            info = stock.info
            dividend_per_share = info.get('dividendRate', 0) or info.get('trailingAnnualDividendRate', 0)

            if dividend_per_share > 0:
                current_yield = (dividend_per_share / latest_price) * 100
                if current_yield >= TARGET_YIELD:
                    buy_signals.append(f'・{symbol}: 利回り{current_yield:.2f}%\n  (価格:{latest_price:.1f}円 / 配当:{dividend_per_share}円)')
        except Exception as e:
            print(f'Skipping {symbol}: {e}')

    # --- 3. Send Notification via LINE ---
    if buy_signals:
        try:
            configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
            message_text = f'📢【利回り{TARGET_YIELD}%超え銘柄】\n\n' + '\n'.join(buy_signals)

            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                push_message_request = PushMessageRequest(
                    to=USER_ID,
                    messages=[TextMessage(text=message_text)]
                )
                line_bot_api.push_message(push_message_request)
            print('✅ LINE notification sent!')
        except Exception as e:
            print(f'LINE transmission error: {e}')
    else:
        print(f'☕️ No stocks found with yield over {TARGET_YIELD}%.')

if __name__ == '__main__':
    main()
