# =====================================================
# IMFS v2.4 – FULL INTERACTIVE STREAMLIT DASHBOARD
# Fixed ticker universe + Stock Picker + Full Valuation Engine
# =====================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np

st.set_page_config(page_title="IMFS v2.4 Dashboard", layout="wide")

# ====================== CONFIG ======================
class IMFS_Config:
    REGIME_PENALTY = 150   # bps — added to WACC in Overheat/Stagflation regime
    ERP = 5.5              # Equity Risk Premium %
    GEO_BUFFER = 150       # Taiwan geopolitical buffer bps
    TRANS_COST = 0.003     # 0.3% transaction cost
    MOS = 0.20             # 20% margin of safety
    RF = 0.015             # Taiwan 10Y risk-free ~1.5%
    TAX_RATE = 0.20        # Taiwan corporate tax 20%
    TERMINAL_GROWTH = 0.02 # DCF terminal growth rate

# ====================== TICKER UNIVERSE (corrected) ======================
TAIWAN_STOCK_UNIVERSE = {
    'Technology': [
        ('2330', 'TSMC',        'Taiwan Semiconductor Manufacturing Co.'),
        ('2317', 'Hon Hai',     'Hon Hai Precision (Foxconn)'),
        ('2454', 'MediaTek',    'MediaTek Inc.'),
        ('2308', 'Delta',       'Delta Electronics'),
        ('2382', 'Quanta',      'Quanta Computer'),
        ('3231', 'Compal',      'Compal Electronics'),
        ('2353', 'Acer',        'Acer Inc.'),
        ('2303', 'UMC',         'United Microelectronics Corp.'),
        ('2409', 'AUO',         'AU Optronics'),
        ('3034', 'Novatek',     'Novatek Microelectronics'),
        ('2379', 'Realtek',     'Realtek Semiconductor'),
        ('2344', 'Winbond',     'Winbond Electronics'),
        ('2357', 'Inventec',    'Inventec Corporation'),
        ('2376', 'Gigabyte',    'Gigabyte Technology'),
        ('3711', 'ASMedia',     'ASMedia Technology'),
    ],
    'Finance': [
        ('2881', 'Fubon',       'Fubon Financial Holdings'),
        ('2882', 'Cathay',      'Cathay Financial Holdings'),
        ('2884', 'E.SUN',       'E.SUN Financial Holdings'),
        ('2885', 'Yuanta',      'Yuanta Financial Holdings'),
        ('2886', 'Mega',        'Mega Financial Holdings'),
        ('2887', 'Taishin',     'Taishin Financial Holdings'),
        ('2888', 'Shin Kong',   'Shin Kong Financial Holdings'),
        ('2890', 'SinoPac',     'SinoPac Financial Holdings'),
        ('2891', 'CTBC',        'CTBC Financial Holdings'),
        ('2892', 'First Fin',   'First Financial Holdings'),
        ('5876', 'Shanghai Com','Shanghai Commercial Bank'),
    ],
    'Telecom & Utilities': [
        ('2412', 'Chunghwa',    'Chunghwa Telecom'),
        ('4904', 'Far EasTone', 'Far EasTone Telecommunications'),
        ('3045', 'TW Mobile',   'Taiwan Mobile'),
        ('6505', 'FPCC',        'Formosa Petrochemical Corp.'),
        ('9945', 'Ruentex',     'Ruentex Development'),
    ],
    'Industrials & Materials': [
        ('2002', 'China Steel', 'China Steel Corporation'),
        ('1301', 'Formosa',     'Formosa Plastics Corp.'),
        ('1303', 'Nan Ya',      'Nan Ya Plastics Corp.'),
        ('1326', 'Formosa Chem','Formosa Chemicals & Fibre'),
        ('2105', 'Cheng Shin',  'Cheng Shin Rubber'),
        ('1402', 'Far Eastern', 'Far Eastern New Century'),
        ('2009', 'Tung Ho',     'Tung Ho Steel Enterprise'),
        ('1434', 'F. Taffeta',  'Formosa Taffeta'),
    ],
    'Consumer & Retail': [
        ('2912', 'President',   'President Chain Store (7-Eleven TW)'),
        ('1216', 'Uni-Pres',    'Uni-President Enterprises'),
        ('2207', 'Hotai Motor', 'Hotai Motor'),
        ('2103', 'Asia Cem',    'Asia Cement'),
        ('9910', 'Feng Tay',    'Feng Tay Enterprises'),
        ('6239', 'Concraft',    'Concraft Holding'),
    ],
}

# Flat lookup: ticker -> (short_name, full_name, sector)
TICKER_LOOKUP: dict[str, tuple[str, str, str]] = {}
for _sector, _stocks in TAIWAN_STOCK_UNIVERSE.items():
    for _t, _s, _f in _stocks:
        TICKER_LOOKUP[_t] = (_s, _f, _sector)

# ====================== REGIME STATE ======================
current_regime  = "Mild Expansion with Overheat/Stagflation Tilt"
current_bias    = "Quality, Low Volatility, Free Cash Flow / Dividend Yield"
current_sectors = ["Finance", "Telecom & Utilities"]

historical_data = {
    'Quarter':        ['2023 Q1-Q2','2023 Q3-Q4','2024 Q1-Q2','2024 Q3-Q4','2025 Q1-Q2','2025 Q3-Q4','2026 Q1'],
    'Regime':         ['Expansion','Expansion','Expansion','Expansion','Mild Expansion/Quality','Mild Expansion/Quality','Mild Expansion/Overheat'],
    'Bias':           ['Growth','Growth','Growth','Growth','Quality/FCF','Quality/FCF','Quality/FCF'],
    'IMFS_Return_%':  [29.0, 26.5, 21.0, 18.5, 21.0, 14.5, 11.0],
    'TAIEX_Return_%': [21.0, 23.5, 17.5, 14.5, 23.5, 13.0, 22.0],
}
df_hist = pd.DataFrame(historical_data)

# ====================== HELPERS ======================

def _is_overheat_regime() -> bool:
    return any(k in current_regime for k in ("Overheat", "Stagflation"))


@st.cache_data(ttl=300)
def fetch_stock_info(ticker: str) -> dict:
    try:
        return yf.Ticker(ticker + ".TW").info
    except Exception:
        return {}


@st.cache_data(ttl=300)
def fetch_cashflow(ticker: str) -> pd.DataFrame:
    try:
        return yf.Ticker(ticker + ".TW").cashflow
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def download_historical_data(tickers: tuple, start_date, end_date) -> dict:
    data = {}
    for ticker in tickers:
        try:
            hist = yf.download(ticker + ".TW", start=start_date, end=end_date, progress=False)
            if not hist.empty:
                data[ticker] = hist['Close']
        except Exception:
            pass
    return data


def _get_cashflow_row(cf: pd.DataFrame, *keys) -> float:
    for key in keys:
        if key in cf.index:
            val = cf.loc[key].iloc[0]
            return float(val) if pd.notna(val) else 0.0
    return 0.0


# ====================== FULL IMFS VALUATION ======================

def run_full_imfs_valuation(ticker: str, company_name: str, sector: str):
    st.subheader(f"IMFS Valuation: {ticker} — {company_name}")

    with st.spinner("Fetching data from Yahoo Finance..."):
        info = fetch_stock_info(ticker)
        cf   = fetch_cashflow(ticker)

    if not info:
        st.error("Could not fetch data. Check ticker or try again.")
        return

    # Market data
    price              = info.get('currentPrice') or info.get('regularMarketPrice') or 0
    shares_outstanding = info.get('sharesOutstanding') or 1
    beta               = info.get('beta') or 1.0
    market_cap         = info.get('marketCap') or (price * shares_outstanding)
    total_debt         = info.get('totalDebt') or 0

    # Owner Earnings = Net Income + D&A - CapEx
    if not cf.empty:
        net_income = _get_cashflow_row(cf, 'Net Income', 'NetIncome')
        da         = _get_cashflow_row(cf, 'Depreciation And Amortization',
                                           'Reconciled Depreciation',
                                           'DepreciationAndAmortization')
        capex      = abs(_get_cashflow_row(cf, 'Capital Expenditure',
                                               'CapitalExpenditures',
                                               'Purchase Of Property Plant And Equipment'))
        owner_earnings = net_income + da - capex
    else:
        net_income = da = capex = 0.0
        owner_earnings = info.get('freeCashflow') or 0

    oe_per_share = owner_earnings / shares_outstanding if shares_outstanding > 0 else 0

    # Regime-adjusted WACC
    rf             = IMFS_Config.RF
    erp            = IMFS_Config.ERP / 100
    geo_buffer     = IMFS_Config.GEO_BUFFER / 10_000
    regime_pen     = IMFS_Config.REGIME_PENALTY / 10_000 if _is_overheat_regime() else 0.0
    cost_of_equity = rf + beta * erp + geo_buffer + regime_pen

    total_capital = market_cap + total_debt
    eq_weight     = market_cap / total_capital if total_capital > 0 else 1.0
    debt_weight   = 1.0 - eq_weight
    interest_exp  = abs(info.get('interestExpense') or 0)
    cost_of_debt  = (interest_exp / total_debt) if total_debt > 0 and interest_exp > 0 else 0.03
    wacc = eq_weight * cost_of_equity + debt_weight * cost_of_debt * (1 - IMFS_Config.TAX_RATE)

    # 5-Year DCF
    raw_growth = info.get('earningsGrowth') or info.get('revenueGrowth') or 0.05
    growth_5y  = max(0.0, min(float(raw_growth), 0.15))
    tg         = IMFS_Config.TERMINAL_GROWTH

    dcf_pv = sum(
        oe_per_share * (1 + growth_5y) ** yr / (1 + wacc) ** yr
        for yr in range(1, 6)
    )
    terminal_cf  = oe_per_share * (1 + growth_5y) ** 5 * (1 + tg)
    terminal_val = (terminal_cf / (wacc - tg)) if wacc > tg else 0.0
    terminal_pv  = terminal_val / (1 + wacc) ** 5

    intrinsic_value = dcf_pv + terminal_pv
    mos_price       = intrinsic_value * (1 - IMFS_Config.MOS)
    upside_pct      = ((intrinsic_value - price) / price * 100) if price > 0 else 0.0

    # Forensic flags
    roe            = info.get('returnOnEquity') or 0
    roa            = info.get('returnOnAssets') or 0
    debt_to_equity = info.get('debtToEquity') or 0
    current_ratio  = info.get('currentRatio') or 0
    op_cashflow    = info.get('operatingCashflow') or 0
    net_inc_info   = info.get('netIncomeToCommon') or 0
    pb             = info.get('priceToBook') or 0
    div_yield      = (info.get('dividendYield') or 0) * 100

    # Piotroski F-Score proxy (max 7)
    pf = sum([
        roe > 0,
        roa > 0,
        op_cashflow > 0,
        op_cashflow > net_inc_info,
        debt_to_equity < 100,
        current_ratio > 1.0,
        (info.get('earningsGrowth') or 0) > 0,
    ])
    pf_label = "Strong (>=5)" if pf >= 5 else "Moderate (3-4)" if pf >= 3 else "Weak (<3)"

    # Beneish accruals proxy
    accruals_ratio = (net_inc_info - op_cashflow) / max(abs(net_inc_info), 1)
    beneish_flag   = "Possible Earnings Inflation" if accruals_ratio > 0.5 else "Clean Accruals"

    # Altman Z proxy
    z_proxy = (roe * 2.0) + (current_ratio * 0.5) + (pb * 0.3)
    z_label = "Distress Zone" if z_proxy < 1.5 else "Grey Zone" if z_proxy < 3.0 else "Safe Zone"

    # Regime fit
    regime_fit   = sector in current_sectors
    regime_label = ("Sector fits current regime" if regime_fit
                    else f"{sector} not preferred — current bias: {current_bias}")

    # Signal
    if price > 0 and price <= mos_price:
        signal = "BUY — Within MOS"
    elif price > 0 and price <= intrinsic_value:
        signal = "HOLD — Below Intrinsic"
    else:
        signal = "AVOID — Above Intrinsic"

    # ── Display ───────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Current Price",         f"NT${price:,.1f}" if price else "N/A")
    c2.metric("Intrinsic Value (DCF)",  f"NT${intrinsic_value:,.1f}" if intrinsic_value else "N/A")
    c3.metric("MOS Price (-20%)",       f"NT${mos_price:,.1f}" if mos_price else "N/A")
    c4.metric("Upside to Intrinsic",    f"{upside_pct:+.1f}%" if price else "N/A")
    c5.metric("Signal",                 signal)

    st.markdown("---")

    st.subheader("WACC Breakdown")
    st.table(pd.DataFrame({
        "Component": ["Risk-Free Rate", "Beta x ERP", "Geo Buffer (TW)",
                      "Regime Penalty", "Cost of Equity", "WACC (blended)"],
        "Value (%)": [
            f"{rf*100:.2f}%",
            f"{beta * IMFS_Config.ERP:.2f}%",
            f"{IMFS_Config.GEO_BUFFER/100:.2f}%",
            f"{IMFS_Config.REGIME_PENALTY/100 if _is_overheat_regime() else 0:.2f}%",
            f"{cost_of_equity*100:.2f}%",
            f"{wacc*100:.2f}%",
        ],
    }))

    st.subheader("Owner Earnings")
    ca, cb, cc, cd = st.columns(4)
    if not cf.empty:
        ca.metric("Net Income",     f"NT${net_income/1e9:.2f}B")
        cb.metric("D&A",            f"NT${da/1e9:.2f}B")
        cc.metric("CapEx",          f"NT${capex/1e9:.2f}B")
        cd.metric("Owner Earnings", f"NT${owner_earnings/1e9:.2f}B")
    else:
        ca.metric("Free Cash Flow (fallback)", f"NT${owner_earnings/1e9:.2f}B")

    st.subheader("DCF Value Breakdown")
    fig_dcf = px.bar(
        pd.DataFrame({
            "Component": ["5-Yr FCF PV", "Terminal Value PV", "Intrinsic Value", "MOS Price (-20%)"],
            "NT$": [dcf_pv, terminal_pv, intrinsic_value, mos_price],
        }),
        x="Component", y="NT$", color="Component", title="DCF Components vs MOS Price"
    )
    if price:
        fig_dcf.add_hline(y=price, line_dash="dash", line_color="red",
                          annotation_text=f"Current Price NT${price:,.1f}")
    st.plotly_chart(fig_dcf, use_container_width=True)

    st.subheader("Forensic Health Check")
    col1, col2, col3 = st.columns(3)
    col1.metric("Piotroski F-Score (proxy)", f"{pf}/7 — {pf_label}")
    col2.metric("Beneish Accruals",          beneish_flag)
    col3.metric("Altman Z (proxy)",          z_label)

    st.table(pd.DataFrame({
        "Metric": ["ROE", "ROA", "Debt/Equity", "Current Ratio", "Div Yield", "P/B"],
        "Value": [
            f"{roe*100:.1f}%" if roe else "N/A",
            f"{roa*100:.1f}%" if roa else "N/A",
            f"{debt_to_equity:.1f}" if debt_to_equity else "N/A",
            f"{current_ratio:.2f}" if current_ratio else "N/A",
            f"{div_yield:.2f}%",
            f"{pb:.2f}" if pb else "N/A",
        ],
    }))

    st.subheader("Regime Compatibility")
    if regime_fit:
        st.success(regime_label)
    else:
        st.warning(regime_label)

    st.markdown("---")
    if st.button(f"Add {ticker} to Watchlist"):
        wl = st.session_state.get("watchlist", [])
        entry = {"Ticker": ticker, "Company": company_name, "Sector": sector,
                 "Price": price, "Intrinsic": round(intrinsic_value, 1),
                 "MOS Price": round(mos_price, 1), "Signal": signal,
                 "Piotroski": f"{pf}/7"}
        if ticker not in [w["Ticker"] for w in wl]:
            wl.append(entry)
            st.session_state["watchlist"] = wl
            st.success(f"{ticker} added to watchlist.")
        else:
            st.info(f"{ticker} is already in the watchlist.")


# ====================== SCANNER ======================

class MarketScanner:
    def __init__(self, sectors_to_scan):
        self.sectors_to_scan = sectors_to_scan

    @st.cache_data(ttl=600)
    def _scan_cached(_self, sectors_tuple, pe_threshold, pb_threshold, div_yield_min):
        results = []
        for sector in sectors_tuple:
            if sector not in TAIWAN_STOCK_UNIVERSE:
                continue
            for ticker, short_name, full_name in TAIWAN_STOCK_UNIVERSE[sector]:
                try:
                    info   = yf.Ticker(ticker + ".TW").info
                    pe     = info.get('trailingPE', float('inf')) or float('inf')
                    pb     = info.get('priceToBook', float('inf')) or float('inf')
                    div    = info.get('dividendYield', 0) or 0
                    price  = info.get('currentPrice', 0)
                    mktcap = info.get('marketCap', 0)
                    score  = (int(pe < pe_threshold) +
                              int(pb < pb_threshold) +
                              int(div > div_yield_min))
                    if score >= 1:
                        results.append({
                            'Ticker':       ticker,
                            'Company':      full_name,
                            'Sector':       sector,
                            'Price':        price,
                            'P/E':          round(pe, 2) if pe != float('inf') else 'N/A',
                            'P/B':          round(pb, 2) if pb != float('inf') else 'N/A',
                            'Div Yield %':  round(div * 100, 2),
                            'Market Cap B': round(mktcap / 1e9, 2) if mktcap else 'N/A',
                            'Score':        score,
                        })
                except Exception:
                    continue
        results.sort(key=lambda x: x['Score'], reverse=True)
        return pd.DataFrame(results) if results else pd.DataFrame()

    def scan(self, pe_threshold=15, pb_threshold=1.2, div_yield_min=0.02):
        return self._scan_cached(
            tuple(self.sectors_to_scan), pe_threshold, pb_threshold, div_yield_min
        )


# ====================== PORTFOLIO HELPERS ======================

def calculate_portfolio_returns(historical_prices, weights):
    df_prices = pd.DataFrame(historical_prices).dropna()
    if df_prices.empty:
        return None, None
    df_returns   = df_prices.pct_change().fillna(0)
    port_returns = (df_returns * weights).sum(axis=1)
    cum_returns  = (1 + port_returns).cumprod() - 1
    return cum_returns, port_returns


# ====================== MAIN DASHBOARD ======================
st.title("IMFS v2.4 - Institutional Regime Rotation Dashboard")
st.caption("Owner Earnings · Regime-Adjusted WACC · Forensic Scoring · Taiwan Market")

page = st.sidebar.selectbox("Navigate", [
    "Main Dashboard",
    "Stock Picker & Valuation",
    "Ticker Quick Valuation",
    "Dynamic Stock Scanner",
    "Portfolio Simulator",
    "Watchlist",
])

# ====================== PAGE 1: MAIN DASHBOARD ======================
if page == "Main Dashboard":
    c1, c2, c3 = st.columns(3)
    c1.metric("Current Regime", current_regime)
    c2.metric("Factor Bias", current_bias)
    c3.metric("Taiwan PMI (Mar 2026)", "53.3", delta="-2.1")

    st.subheader("Immediate Actions (April 2026)")
    st.info("""
    - Rebalance 60-80% into Quality/FCF/Dividend tilt
    - Focus on Finance and Telecom & Utilities sectors
    - Target 20% margin of safety (MOS price from Stock Picker)
    - Regime penalty of +150 bps applied to WACC this quarter
    """)

    st.subheader("Risk Matrix")
    st.table(pd.DataFrame({
        "Risk":        ["Regime Shift", "Geopolitical", "Inflation Spike", "Liquidity"],
        "Probability": ["Medium", "High", "Medium-High", "Medium"],
        "Mitigation":  ["Quarterly PMI check", "+150 bps geo buffer",
                        "+150 bps regime penalty", "Large-cap focus"],
    }))

    st.subheader("Quarterly Performance (Illustrative)")
    st.dataframe(df_hist, use_container_width=True)
    fig = px.bar(df_hist, x='Quarter', y=['IMFS_Return_%', 'TAIEX_Return_%'],
                 title="IMFS v2.4 vs TAIEX Returns (%)", barmode='group')
    st.plotly_chart(fig, use_container_width=True)

# ====================== PAGE 2: STOCK PICKER & VALUATION ======================
elif page == "Stock Picker & Valuation":
    st.header("Taiwan Stock Picker & Full IMFS Valuation")
    st.write(
        "Search by ticker number or company name. "
        "Select a stock to run a full Owner Earnings DCF with regime-adjusted WACC."
    )

    all_stocks = [
        {"ticker": t, "short": s, "full": f, "sector": sec,
         "display": f"{t} - {f}  [{sec}]"}
        for sec, stocks in TAIWAN_STOCK_UNIVERSE.items()
        for t, s, f in stocks
    ]

    search = st.text_input(
        "Search ticker or company name (e.g. '2330' or 'TSMC' or 'Finance')", ""
    )
    q = search.strip().lower()
    filtered = (
        [x for x in all_stocks
         if q in x["ticker"] or q in x["full"].lower()
         or q in x["short"].lower() or q in x["sector"].lower()]
        if q else all_stocks
    )

    if not filtered:
        st.warning("No matching stocks found.")
    else:
        chosen_display = st.selectbox(
            f"Select from {len(filtered)} result(s)",
            [x["display"] for x in filtered],
        )
        chosen = next(x for x in filtered if x["display"] == chosen_display)

        ca, cb, cc = st.columns(3)
        ca.markdown(f"**Ticker:** `{chosen['ticker']}.TW`")
        cb.markdown(f"**Sector:** {chosen['sector']}")
        cc.markdown(
            f"**Regime fit:** {'Yes' if chosen['sector'] in current_sectors else 'No'}"
        )

        if st.button("Run Full IMFS Valuation", type="primary"):
            run_full_imfs_valuation(chosen["ticker"], chosen["full"], chosen["sector"])

# ====================== PAGE 3: TICKER QUICK VALUATION ======================
elif page == "Ticker Quick Valuation":
    st.header("Quick Ticker Lookup")
    ticker_input = st.text_input("Enter TWSE Ticker (e.g. 2881, 2330)", "2881")
    if st.button("Fetch"):
        info = fetch_stock_info(ticker_input)
        if info:
            _, full, _ = TICKER_LOOKUP.get(ticker_input, ("", ticker_input, "Unknown"))
            st.write(f"**Company:** {info.get('longName', full)}")
            st.write(f"**Price:** NT${info.get('currentPrice', 'N/A')}")
            st.write(f"**Trailing P/E:** {info.get('trailingPE', 'N/A')}")
            st.write(f"**P/B:** {info.get('priceToBook', 'N/A')}")
            st.write(f"**Div Yield:** {(info.get('dividendYield') or 0)*100:.2f}%")
        else:
            st.error("Could not fetch data.")

# ====================== PAGE 4: DYNAMIC STOCK SCANNER ======================
elif page == "Dynamic Stock Scanner":
    st.header("Dynamic Market Scanner - Regime-Aware Stock Discovery")

    col1, col2 = st.columns([2, 1])
    with col1:
        selected_sectors = st.multiselect(
            "Sectors to scan",
            options=list(TAIWAN_STOCK_UNIVERSE.keys()),
            default=current_sectors,
        )
    with col2:
        scan_button = st.button("Scan Market Now", type="primary")

    if selected_sectors and scan_button:
        pe_t, pb_t, dy_min = (12, 1.0, 0.03) if "Quality" in current_bias else (18, 1.5, 0.02)
        with st.spinner("Scanning Taiwan market..."):
            results = MarketScanner(selected_sectors).scan(pe_t, pb_t, dy_min)

        if not results.empty:
            st.success(f"Found {len(results)} candidates.")
            st.dataframe(results, use_container_width=True)
            st.plotly_chart(
                px.bar(
                    results.groupby('Sector').size().reset_index(name='Count'),
                    x='Sector', y='Count', color='Count', title="Candidates by Sector",
                ),
                use_container_width=True,
            )
        else:
            st.warning("No candidates found with current thresholds.")

# ====================== PAGE 5: PORTFOLIO SIMULATOR ======================
elif page == "Portfolio Simulator":
    st.header("Portfolio Backtest Simulator")

    col1, col2 = st.columns(2)
    with col1:
        backtest_years = st.slider("Backtest Period (years)", 1, 5, 3)
    with col2:
        strategy = st.selectbox("Strategy", [
            "Growth (2330, 2308, 3231)",
            "Quality/Dividend (2881, 2412, 2882)",
            "Balanced (2330, 2881, 2308)",
        ])

    strategy_map = {
        "Growth (2330, 2308, 3231)":           (["2330","2308","3231"], np.array([0.40,0.35,0.25]), "Growth"),
        "Quality/Dividend (2881, 2412, 2882)": (["2881","2412","2882"], np.array([0.40,0.35,0.25]), "Quality/Dividend"),
        "Balanced (2330, 2881, 2308)":         (["2330","2881","2308"], np.array([0.33,0.33,0.34]), "Balanced"),
    }
    tickers, weights, name = strategy_map[strategy]

    end_dt   = datetime.now()
    start_dt = end_dt - timedelta(days=365 * backtest_years)
    st.info(f"Backtesting **{name}** from {start_dt.date()} to {end_dt.date()}")

    prices = download_historical_data(tuple(tickers), start_dt, end_dt)
    if prices:
        cum_ret, daily_ret = calculate_portfolio_returns(prices, weights)
        if cum_ret is not None:
            total_ret = cum_ret.iloc[-1] * 100
            ann_ret   = ((1 + cum_ret.iloc[-1]) ** (1 / backtest_years) - 1) * 100
            vol       = daily_ret.std() * np.sqrt(252) * 100
            sharpe    = (ann_ret - 2.0) / vol if vol > 0 else 0
            max_dd    = (cum_ret.cummax() - cum_ret).max() * 100

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Total Return",  f"{total_ret:.1f}%")
            c2.metric("Annualised",    f"{ann_ret:.1f}%")
            c3.metric("Volatility",    f"{vol:.1f}%")
            c4.metric("Sharpe",        f"{sharpe:.2f}")
            c5.metric("Max Drawdown",  f"-{max_dd:.1f}%")

            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(
                x=cum_ret.index, y=cum_ret.values * 100,
                mode='lines', name=name, fill='tozeroy',
            ))
            fig3.update_layout(title=f"{name} - Cumulative Return (%)",
                               xaxis_title="Date", yaxis_title="Return (%)", height=400)
            st.plotly_chart(fig3, use_container_width=True)
    else:
        st.warning("Could not download price data.")

# ====================== PAGE 6: WATCHLIST ======================
elif page == "Watchlist":
    st.header("Watchlist")
    wl = st.session_state.get("watchlist", [])
    if wl:
        st.dataframe(pd.DataFrame(wl), use_container_width=True)
        if st.button("Clear Watchlist"):
            st.session_state["watchlist"] = []
            st.rerun()
    else:
        st.info("No stocks in watchlist yet. Run a valuation and click 'Add to Watchlist'.")

st.markdown("---")
st.caption("IMFS v2.4 | Owner Earnings · Regime-Adjusted WACC · Forensic Scoring · Taiwan Market")
