import os
import json
import pandas as pd
import yfinance as ticker
import gspread
from google.oauth2.service_account import Credentials
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, PushMessageRequest, TextMessage

def main():
    # --- 設定と認証 ---
    CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    USER_ID = os.getenv('LINE_USER_ID')
    # GitHub SecretsからJSONとURLを取得
    SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    SPREADSHEET_URL = os.getenv('SPREADSHEET_URL')
    
    CSV_FILE = './assetbalance(JP)_20260220_201541.csv'
    TARGET_YIELD = 3.5

    if not all([CHANNEL_ACCESS_TOKEN, USER_ID, SERVICE_ACCOUNT_JSON, SPREADSHEET_URL]):
        print('Error: Required environment variables are missing.')
        return

    # スプレッドシート認証
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    credentials = Credentials.from_service_account_info(json.loads(SERVICE_ACCOUNT_JSON), scopes=scopes)
    gc = gspread.authorize(credentials)
    sh = gc.open_by_url(SPREADSHEET_URL)
    worksheet = sh.get_worksheet(0) # 1番目のシート

    # --- 1. CSVから銘柄抽出 ---
    try:
        df = pd.read_csv(CSV_FILE, encoding='shift_jis', skiprows=6, on_bad_lines='skip')
        codes = [str(code) + '.T' for code in df['銘柄コード'].unique() if str(code).isdigit()]
    except Exception as e:
        print(f'CSV reading error: {e}')
        codes = []

    # --- 2. 利回りチェックとデータ作成 ---
    buy_signals = []
    rows_to_append = []
    now = pd.Timestamp.now(tz='Asia/Tokyo').strftime('%Y-%m-%d %H:%M')

    for symbol in codes:
        try:
            stock = ticker.Ticker(symbol)
            hist = stock.history(period='1d')
            if hist.empty: continue
            
            latest_price = hist['Close'].iloc[-1]
            info = stock.info
            div_rate = info.get('dividendRate', 0) or info.get('trailingAnnualDividendRate', 0)

            if div_rate > 0:
                current_yield = (div_rate / latest_price) * 100
                # 全銘柄のデータをスプレッドシート用リストに追加
                rows_to_append.append([now, symbol, latest_price, div_rate, round(current_yield, 2)])
                
                if current_yield >= TARGET_YIELD:
                    buy_signals.append(f'・{symbol}: 利回り{current_yield:.2f}%\n  (価格:{latest_price:.1f}円 / 配当:{div_rate}円)')
        except Exception as e:
            print(f'Skipping {symbol}: {e}')

    # --- 3. スプレッドシートへ書き込み ---
    if rows_to_append:
        worksheet.append_rows(rows_to_append)
        print('✅ Spreadsheet updated!')

    # --- 4. LINE通知 ---
    if buy_signals:
        try:
            configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
            message_text = f'📢【利回り{TARGET_YIELD}%超え銘柄】\n\n' + '\n'.join(buy_signals)
            message_text += f'\n\n📊 スプレッドシートに詳細を記録しました！\n{SPREADSHEET_URL}'

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
