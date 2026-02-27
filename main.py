import os
import pandas as pd
import yfinance as ticker
import matplotlib.pyplot as plt

CSV_FILE = './assetbalance(JP)_20260220_201541.csv'
TARGET_YIELD = 3.5
plots_dir = 'plots'

def main():
    os.makedirs(plots_dir, exist_ok=True)

    try:
        df = pd.read_csv(CSV_FILE, encoding='shift_jis', skiprows=6, on_bad_lines='skip')
        codes = [str(code) + '.T' for code in df['銘柄コード'].unique() if str(code).isdigit()]
    except Exception as e:
        print(f'CSV reading error: {e}')
        return

    for symbol in codes:
        try:
            stock = ticker.Ticker(symbol)
            latest_price = stock.history(period='1d')['Close'].iloc[-1]
            info = stock.info
            dividend_per_share = info.get('dividendRate', 0) or info.get('trailingAnnualDividendRate', 0)

            if dividend_per_share <= 0 or latest_price <= 0:
                continue

            current_yield = (dividend_per_share / latest_price) * 100

            if current_yield < TARGET_YIELD:
                continue

            historical_data = stock.history(period="2y")
            if historical_data.empty:
                continue

            years = sorted(historical_data.index.year.unique())
            yields = []

            for year in years:
                yearly_data = historical_data[historical_data.index.year == year]
                yearly_div = yearly_data['Dividends'].sum()
                yearly_avg = yearly_data['Close'].mean()
                if yearly_avg > 0:
                    yields.append((yearly_div / yearly_avg) * 100)

            if not yields:
                continue

            avg_yield = sum(yields) / len(yields)

            plot_path = os.path.join(plots_dir, f'{symbol}_yield_plot.png')

            plt.figure(figsize=(10, 6))
            plt.plot(years[:len(yields)], yields, marker='o')
            plt.axhline(y=avg_yield, linestyle='--')
            plt.title(f'{symbol} Dividend Yield')
            plt.xlabel('Year')
            plt.ylabel('Yield (%)')
            plt.tight_layout()
            plt.savefig(plot_path)
            plt.close()

            print(f'Generated: {plot_path}')

        except Exception as e:
            print(f'Skipping {symbol}: {e}')

if __name__ == '__main__':
    main()
