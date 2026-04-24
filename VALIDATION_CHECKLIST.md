# TWSE Integration Validation Checklist

## Data Model

- `price` comes from TWSE `STOCK_DAY_ALL` when available.
- `sharesOutstanding` comes from TWSE `t187ap03_L`.
- `priceToBook`, `trailingPE`, and `dividendYield` come from TWSE `BWIBBU_ALL`.
- `revenueGrowth` comes from TWSE `t187ap05_L` year-over-year monthly revenue growth.
- `currentRatio`, `debtToEquity`, `returnOnEquity`, and `returnOnAssets` are derived from TWSE balance sheet and statement data.
- `trailingEps` is derived from official TWSE price and P/E when available.

## Endpoint Mapping

- `t187ap03_L`: listed company basics and issued shares
- `STOCK_DAY_ALL`: official latest close and trade date
- `BWIBBU_ALL`: P/E, P/B, dividend yield
- `t187ap05_L`: monthly revenue growth proxy
- `t187ap06_L_*`: latest income statement by industry family
- `t187ap07_L_*`: latest balance sheet by industry family
- `t187ap45_L`: dividend fallback when yield is missing

## UI Behavior

- If official price verification fails, valuation must stop with a clear error.
- If cash flow is available, valuation mode should be `DCF` or `FCF`.
- If cash flow is missing but official EPS exists, valuation mode should switch to `EPS 法`.
- If valuation quality is insufficient, buy-zone metrics must show `N/A`.
- When valuation is not usable, DCF/WACC/owner-earnings breakdown sections must be hidden.

## Manual Cases

- `2330`: verify TWSE-backed price, P/B, dividend yield, and non-empty valuation mode.
- `2886`: verify financial-sector fallback fields and EPS-mode behavior if cash flow is unavailable.
- `2412`: verify dividend yield and price verification caption.
- A ticker with weak or missing statements: confirm valuation is blocked without contradictory charts.

## Push Gate

- `python -m py_compile imfs_dashboard.py twse_data.py`
- Validate scanner still runs and uses official P/E, P/B, and yield data.
- Validate valuation page shows one consistent mode only: `DCF`, `FCF`, `EPS 法`, or blocked.
