import os
import pandas as pd
import yfinance as ticker
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, PushMessageRequest, TextMessage, ImageMessage # ImageMessage を追加
import matplotlib.pyplot as plt

def main():
    # --- Configuration from Environment Variables ---
    CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    USER_ID = os.getenv('LINE_USER_ID')
    GITHUB_USERNAME = os.getenv('GITHUB_USERNAME') # New environment variable
    GITHUB_REPOSITORY = os.getenv('GITHUB_REPOSITORY') # New environment variable
    CSV_FILE = './assetbalance(JP)_20260220_201541.csv'
    TARGET_YIELD = 3.5

    if not CHANNEL_ACCESS_TOKEN or not USER_ID:
        print('Error: LINE_CHANNEL_ACCESS_TOKEN or LINE_USER_ID environment variables are not set.')
        return

    plots_dir = 'plots'
    os.makedirs(plots_dir, exist_ok=True)

    try:
        df = pd.read_csv(CSV_FILE, encoding='shift_jis', skiprows=6, on_bad_lines='skip')
        codes = [str(code) + '.T' for code in df['銘柄コード'].unique() if str(code).isdigit()]
    except Exception as e:
        print(f'CSV reading error: {e}')
        codes = []

    buy_signals = []
    plot_files = [] # 生成されたプロットファイルのリストを保持

    for symbol in codes:
        try:
            stock = ticker.Ticker(symbol)
            latest_price = stock.history(period='1d')['Close'].iloc[-1]
            info = stock.info
            dividend_per_share = info.get('dividendRate', 0) or info.get('trailingAnnualDividendRate', 0)

            current_yield = 0
            if dividend_per_share > 0 and latest_price > 0:
                current_yield = (dividend_per_share / latest_price) * 100

            historical_data = stock.history(period="2y")
            historical_yields_list = []
            years_for_plot = []

            if not historical_data.empty:
                years_in_history = sorted(historical_data.index.year.unique())

                for year in years_in_history:
                    yearly_data = historical_data[historical_data.index.year == year]

                    if not yearly_data.empty:
                        yearly_dividends_sum = yearly_data['Dividends'].sum()
                        yearly_avg_price = yearly_data['Close'].mean()

                        if yearly_avg_price > 0:
                            yearly_yield = (yearly_dividends_sum / yearly_avg_price) * 100
                            historical_yields_list.append(yearly_yield)
                            years_for_plot.append(year)

            average_historical_yield = 0
            if historical_yields_list:
                average_historical_yield = sum(historical_yields_list) / len(historical_yields_list)

            undervalued_status = "N/A"
            if current_yield > 0 and average_historical_yield > 0:
                if current_yield > average_historical_yield:
                    undervalued_status = "✨ Undervalued! (Current Yield > Historical Average)"
                else:
                    undervalued_status = "Not Undervalued (Current Yield <= Historical Average)"
            elif current_yield > 0 and average_historical_yield == 0:
                 undervalued_status = "Potentially Undervalued (No historical dividend baseline available)"

            if current_yield >= TARGET_YIELD:
                plot_filename = os.path.join(plots_dir, f'{symbol}_yield_plot.png')
                if years_for_plot and historical_yields_list:
                    plt.figure(figsize=(10, 6))
                    plt.plot(years_for_plot, historical_yields_list, marker='o', linestyle='-', label='Historical Annual Yield')
                    plt.axhline(y=average_historical_yield, color='r', linestyle='--', label=f'Average Historical Yield ({average_historical_yield:.2f}%)')
                    plt.plot(years_for_plot[-1] + 0.5, current_yield, 'X', color='g', markersize=10, label=f'Current Yield ({current_yield:.2f}%)')

                    plt.title(f'Dividend Yield for {symbol}\n{undervalued_status}')
                    plt.xlabel('Year')
                    plt.ylabel('Dividend Yield (%)')
                    plt.grid(True)
                    plt.legend()
                    plt.tight_layout()
                    plt.savefig(plot_filename)
                    plot_files.append(plot_filename)
                    plt.close() # Close the plot to free memory

                buy_signals.append(f'・{symbol}: 利回り{current_yield:.2f}% (目標:{TARGET_YIELD}%)\n  (価格:{latest_price:.1f}円 / 配当:{dividend_per_share}円) {undervalued_status}')

        except Exception as e:
            print(f'Skipping {symbol}: {e}')

    # --- 3. Send Notification via LINE ---
    if buy_signals:
        try:
            configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
            
            messages_to_send = []

            # テキストメッセージ
            message_text = f'📢【利回り{TARGET_YIELD}%超え銘柄】\n\n' + '\n'.join(buy_signals)
            if plot_files:
                message_text += '\n\n📈 詳細は以下の画像をご覧ください！'
            messages_to_send.append(TextMessage(text=message_text))

            # 画像メッセージ（GitHub PagesのURLを構築）
            if GITHUB_USERNAME and GITHUB_REPOSITORY:
                base_url = f'https://{GITHUB_USERNAME}.github.io/{GITHUB_REPOSITORY}/plots/'
                for plot_file in plot_files[:4]:
                    image_filename = os.path.basename(plot_file)
                    image_public_url = f'{base_url}{image_filename}'
                    messages_to_send.append(ImageMessage(original_content_url=image_public_url, preview_image_url=image_public_url))
            else:
                print("Warning: GITHUB_USERNAME or GITHUB_REPOSITORY not set. Cannot construct public image URLs.")


            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                push_message_request = PushMessageRequest(
                    to=USER_ID,
                    messages=messages_to_send
                )
                line_bot_api.push_message(push_message_request)
            print('✅ LINE notification sent!')
        except Exception as e:
            print(f'LINE transmission error: {e}')
    else:
        print(f'☕️ No stocks found with yield over {TARGET_YIELD}%.')

if __name__ == '__main__':
    main()
