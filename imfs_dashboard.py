# =====================================================
# IMFS v2.4 – 機構級台股輪動儀表板（繁體中文版）
# 修正投資組合模擬器 + 完整方法論說明
# =====================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np

st.set_page_config(page_title="IMFS v2.4 台股儀表板", layout="wide")

# ====================== 參數設定 ======================
class IMFS_Config:
    REGIME_PENALTY = 150   # bps — 過熱/滯脹時加入 WACC
    ERP            = 5.5   # 股權風險溢價 %
    GEO_BUFFER     = 150   # 台灣地緣政治緩衝 bps
    TRANS_COST     = 0.003 # 交易成本 0.3%
    MOS            = 0.20  # 安全邊際 20%
    RF             = 0.015 # 台灣10年期無風險利率 ~1.5%
    TAX_RATE       = 0.20  # 台灣企業所得稅 20%
    TERMINAL_GROWTH= 0.02  # DCF 永續成長率

# ====================== 台股標的（已校正） ======================
TAIWAN_STOCK_UNIVERSE = {
    '科技類': [
        ('2330', 'TSMC',    '台灣積體電路製造'),
        ('2317', '鴻海',    '鴻海精密工業'),
        ('2454', '聯發科',  '聯發科技'),
        ('2308', '台達電',  '台達電子工業'),
        ('2382', '廣達',    '廣達電腦'),
        ('3231', '緯創',    '緯創資通'),
        ('2353', '宏碁',    '宏碁股份有限公司'),
        ('2303', '聯電',    '聯華電子'),
        ('2409', '友達',    '友達光電'),
        ('3034', '聯詠',    '聯詠科技'),
        ('2379', '瑞昱',    '瑞昱半導體'),
        ('2344', '華邦電',  '華邦電子'),
        ('2357', '英業達',  '英業達股份有限公司'),
        ('2376', '技嘉',    '技嘉科技'),
        ('3711', '創意',    '創意電子'),
    ],
    '金融類': [
        ('2881', '富邦金',  '富邦金融控股'),
        ('2882', '國泰金',  '國泰金融控股'),
        ('2884', '玉山金',  '玉山金融控股'),
        ('2885', '元大金',  '元大金融控股'),
        ('2886', '兆豐金',  '兆豐金融控股'),
        ('2887', '台新金',  '台新金融控股'),
        ('2888', '新光金',  '新光金融控股'),
        ('2890', '永豐金',  '永豐金融控股'),
        ('2891', '中信金',  '中國信託金融控股'),
        ('2892', '第一金',  '第一金融控股'),
        ('5876', '上海商銀','上海商業儲蓄銀行'),
    ],
    '電信與公用事業': [
        ('2412', '中華電',  '中華電信'),
        ('4904', '遠傳',    '遠傳電信'),
        ('3045', '台灣大',  '台灣大哥大'),
        ('6505', '台塑化',  '台灣塑膠化學工業'),
        ('9945', '潤泰全',  '潤泰全球'),
    ],
    '工業與原材料': [
        ('2002', '中鋼',    '中國鋼鐵'),
        ('1301', '台塑',    '台灣塑膠工業'),
        ('1303', '南亞',    '南亞塑膠工業'),
        ('1326', '台化',    '台灣化學纖維'),
        ('2105', '正新',    '正新橡膠工業'),
        ('1402', '遠東新',  '遠東新世紀'),
        ('2009', '東和鋼鐵','東和鋼鐵企業'),
        ('1434', '福懋',    '福懋興業'),
    ],
    '消費與零售': [
        ('2912', '統一超',  '統一超商（7-ELEVEN）'),
        ('1216', '統一',    '統一企業'),
        ('2207', '和泰車',  '和泰汽車'),
        ('2103', '亞泥',    '亞洲水泥'),
        ('9910', '豐泰',    '豐泰企業'),
        ('6239', '力成',    '力成科技'),
    ],
}

TICKER_LOOKUP: dict[str, tuple[str, str, str]] = {}
for _sector, _stocks in TAIWAN_STOCK_UNIVERSE.items():
    for _t, _s, _f in _stocks:
        TICKER_LOOKUP[_t] = (_s, _f, _sector)

# ====================== 當前景氣狀態 ======================
current_regime  = "溫和擴張（過熱/滯脹傾向）"
current_bias    = "品質、低波動、自由現金流 / 股息殖利率"
current_sectors = ["金融類", "電信與公用事業"]

historical_data = {
    '季度':         ['2023 Q1-Q2','2023 Q3-Q4','2024 Q1-Q2','2024 Q3-Q4','2025 Q1-Q2','2025 Q3-Q4','2026 Q1'],
    '景氣狀態':     ['擴張','擴張','擴張','擴張','溫和擴張/品質','溫和擴張/品質','溫和擴張/過熱'],
    '因子偏好':     ['成長','成長','成長','成長','品質/自由現金流','品質/自由現金流','品質/自由現金流'],
    'IMFS報酬_%':   [29.0, 26.5, 21.0, 18.5, 21.0, 14.5, 11.0],
    '加權指數報酬_%':[21.0, 23.5, 17.5, 14.5, 23.5, 13.0, 22.0],
}
df_hist = pd.DataFrame(historical_data)

# ====================== 工具函數 ======================

def _is_overheat_regime() -> bool:
    return any(k in current_regime for k in ("過熱", "滯脹"))


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
    """下載歷史價格；相容新舊版 yfinance MultiIndex 欄位"""
    data = {}
    for ticker in tickers:
        try:
            hist = yf.download(ticker + ".TW", start=start_date,
                               end=end_date, progress=False, auto_adjust=True)
            if hist.empty:
                continue
            close = hist["Close"]
            # 新版 yfinance 單一標的仍可能回傳 DataFrame
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            close = close.squeeze()
            if isinstance(close, pd.Series) and not close.empty:
                data[ticker] = close
        except Exception:
            pass
    return data


def _get_cashflow_row(cf: pd.DataFrame, *keys) -> float:
    for key in keys:
        if key in cf.index:
            val = cf.loc[key].iloc[0]
            return float(val) if pd.notna(val) else 0.0
    return 0.0


# ====================== 完整 IMFS 估值 ======================

def run_full_imfs_valuation(ticker: str, company_name: str, sector: str):
    st.subheader(f"IMFS 估值：{ticker} — {company_name}")

    with st.spinner("正在從 Yahoo Finance 取得資料..."):
        info = fetch_stock_info(ticker)
        cf   = fetch_cashflow(ticker)

    if not info:
        st.error("無法取得資料，請確認股票代號後再試。")
        return

    price              = info.get('currentPrice') or info.get('regularMarketPrice') or 0
    shares_outstanding = info.get('sharesOutstanding') or 1
    beta               = info.get('beta') or 1.0
    market_cap         = info.get('marketCap') or (price * shares_outstanding)
    total_debt         = info.get('totalDebt') or 0

    # 業主盈餘 = 淨利 + 折舊攤銷 - 資本支出
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

    # 景氣調整後 WACC
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

    # 5年 DCF
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

    # 財務品質指標
    roe            = info.get('returnOnEquity') or 0
    roa            = info.get('returnOnAssets') or 0
    debt_to_equity = info.get('debtToEquity') or 0
    current_ratio  = info.get('currentRatio') or 0
    op_cashflow    = info.get('operatingCashflow') or 0
    net_inc_info   = info.get('netIncomeToCommon') or 0
    pb             = info.get('priceToBook') or 0
    div_yield      = (info.get('dividendYield') or 0) * 100

    # Piotroski F-Score 代理（最高7分）
    pf = sum([
        roe > 0,
        roa > 0,
        op_cashflow > 0,
        op_cashflow > net_inc_info,
        debt_to_equity < 100,
        current_ratio > 1.0,
        (info.get('earningsGrowth') or 0) > 0,
    ])
    pf_label = "強健 (>=5)" if pf >= 5 else "普通 (3-4)" if pf >= 3 else "偏弱 (<3)"

    accruals_ratio = (net_inc_info - op_cashflow) / max(abs(net_inc_info), 1)
    beneish_flag   = "⚠️ 疑似盈餘虛增" if accruals_ratio > 0.5 else "✅ 應計項目正常"

    z_proxy = (roe * 2.0) + (current_ratio * 0.5) + (pb * 0.3)
    z_label = "⚠️ 財務危機區" if z_proxy < 1.5 else "🟡 灰色地帶" if z_proxy < 3.0 else "✅ 財務安全"

    regime_fit   = sector in current_sectors
    regime_label = ("✅ 符合當前景氣偏好" if regime_fit
                    else f"⚠️ {sector} 非當前偏好板塊 — 建議偏向：{current_bias}")

    if price > 0 and price <= mos_price:
        signal = "買進 — 低於安全邊際價"
    elif price > 0 and price <= intrinsic_value:
        signal = "持有 — 低於內在價值"
    else:
        signal = "觀望 — 高於內在價值"

    # ── 顯示 ──
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("目前股價",       f"NT${price:,.1f}" if price else "N/A")
    c2.metric("內在價值 (DCF)", f"NT${intrinsic_value:,.1f}" if intrinsic_value else "N/A")
    c3.metric("安全邊際價 (-20%)", f"NT${mos_price:,.1f}" if mos_price else "N/A")
    c4.metric("距內在價值漲幅", f"{upside_pct:+.1f}%" if price else "N/A")
    c5.metric("投資訊號",       signal)

    st.markdown("---")

    st.subheader("WACC 拆解")
    st.table(pd.DataFrame({
        "組成項目": ["無風險利率", "Beta × 股權風險溢價", "地緣政治緩衝（台灣）",
                     "景氣懲罰溢價", "→ 股權成本", "WACC（加權）"],
        "數值 (%)": [
            f"{rf*100:.2f}%",
            f"{beta * IMFS_Config.ERP:.2f}%",
            f"{IMFS_Config.GEO_BUFFER/100:.2f}%",
            f"{IMFS_Config.REGIME_PENALTY/100 if _is_overheat_regime() else 0:.2f}%",
            f"{cost_of_equity*100:.2f}%",
            f"{wacc*100:.2f}%",
        ],
    }))

    st.subheader("業主盈餘（Owner Earnings）")
    ca, cb, cc, cd = st.columns(4)
    if not cf.empty:
        ca.metric("淨利",       f"NT${net_income/1e9:.2f}B")
        cb.metric("折舊＋攤銷", f"NT${da/1e9:.2f}B")
        cc.metric("資本支出",   f"NT${capex/1e9:.2f}B")
        cd.metric("業主盈餘",   f"NT${owner_earnings/1e9:.2f}B")
    else:
        ca.metric("自由現金流（替代）", f"NT${owner_earnings/1e9:.2f}B")

    st.subheader("DCF 估值拆解")
    fig_dcf = px.bar(
        pd.DataFrame({
            "項目": ["5年現金流現值", "永續價值現值", "內在價值", "安全邊際價 (-20%)"],
            "NT$":  [dcf_pv, terminal_pv, intrinsic_value, mos_price],
        }),
        x="項目", y="NT$", color="項目", title="DCF 估值 vs 安全邊際價"
    )
    if price:
        fig_dcf.add_hline(y=price, line_dash="dash", line_color="red",
                          annotation_text=f"目前股價 NT${price:,.1f}")
    st.plotly_chart(fig_dcf, use_container_width=True)

    st.subheader("財務健全度（法醫會計）")
    col1, col2, col3 = st.columns(3)
    col1.metric("Piotroski F-Score（代理）", f"{pf}/7 — {pf_label}")
    col2.metric("Beneish 應計項目",          beneish_flag)
    col3.metric("Altman Z（代理）",          z_label)

    st.table(pd.DataFrame({
        "指標": ["ROE 股東權益報酬率", "ROA 資產報酬率", "負債/權益比",
                  "流動比率", "股息殖利率", "股價淨值比 P/B"],
        "數值": [
            f"{roe*100:.1f}%" if roe else "N/A",
            f"{roa*100:.1f}%" if roa else "N/A",
            f"{debt_to_equity:.1f}" if debt_to_equity else "N/A",
            f"{current_ratio:.2f}" if current_ratio else "N/A",
            f"{div_yield:.2f}%",
            f"{pb:.2f}" if pb else "N/A",
        ],
    }))

    st.subheader("景氣適配性")
    if regime_fit:
        st.success(regime_label)
    else:
        st.warning(regime_label)

    st.markdown("---")
    if st.button(f"➕ 加入觀察清單：{ticker}"):
        wl = st.session_state.get("watchlist", [])
        entry = {"股票代號": ticker, "公司名稱": company_name, "板塊": sector,
                 "股價": price, "內在價值": round(intrinsic_value, 1),
                 "安全邊際價": round(mos_price, 1), "訊號": signal,
                 "Piotroski": f"{pf}/7"}
        if ticker not in [w["股票代號"] for w in wl]:
            wl.append(entry)
            st.session_state["watchlist"] = wl
            st.success(f"{ticker} 已加入觀察清單。")
        else:
            st.info(f"{ticker} 已在觀察清單中。")


# ====================== 動態掃描器 ======================

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
                            '股票代號':   ticker,
                            '公司名稱':   full_name,
                            '板塊':       sector,
                            '股價':       price,
                            'P/E':        round(pe, 2) if pe != float('inf') else 'N/A',
                            'P/B':        round(pb, 2) if pb != float('inf') else 'N/A',
                            '殖利率 %':   round(div * 100, 2),
                            '市值（十億）':round(mktcap / 1e9, 2) if mktcap else 'N/A',
                            '評分':       score,
                        })
                except Exception:
                    continue
        results.sort(key=lambda x: x['評分'], reverse=True)
        return pd.DataFrame(results) if results else pd.DataFrame()

    def scan(self, pe_threshold=15, pb_threshold=1.2, div_yield_min=0.02):
        return self._scan_cached(
            tuple(self.sectors_to_scan), pe_threshold, pb_threshold, div_yield_min
        )


# ====================== 投資組合計算 ======================

def calculate_portfolio_returns(historical_prices: dict, weights: np.ndarray):
    """對齊各股價格序列後計算組合報酬"""
    if not historical_prices:
        return None, None
    # 確保每個值都是一維 Series
    clean = {}
    for k, v in historical_prices.items():
        s = v.squeeze() if hasattr(v, 'squeeze') else v
        if isinstance(s, pd.Series):
            clean[k] = s
    if not clean:
        return None, None

    df_prices = pd.DataFrame(clean).dropna()
    if df_prices.empty or df_prices.shape[1] == 0:
        return None, None

    # 權重需與實際欄位數對齊（部分標的可能抓不到資料）
    actual_cols = df_prices.shape[1]
    w = weights[:actual_cols]
    w = w / w.sum()  # 重新正規化

    df_returns   = df_prices.pct_change().fillna(0)
    port_returns = (df_returns * w).sum(axis=1)
    cum_returns  = (1 + port_returns).cumprod() - 1
    return cum_returns, port_returns


# ====================== 主程式 ======================
st.title("IMFS v2.4 — 機構級台股景氣輪動儀表板")
st.caption("業主盈餘 · 景氣調整 WACC · 法醫會計評分 · 台灣市場專用")

page = st.sidebar.selectbox("功能選單", [
    "📊 主儀表板",
    "🏷️ 選股與完整估值",
    "🔍 快速查詢",
    "🎯 動態股票掃描",
    "📈 投資組合模擬",
    "📋 觀察清單",
    "📖 方法論說明",
])

# ====================== 主儀表板 ======================
if page == "📊 主儀表板":
    c1, c2, c3 = st.columns(3)
    c1.metric("當前景氣狀態", current_regime)
    c2.metric("因子偏好", current_bias)
    c3.metric("台灣製造業 PMI（2026年3月）", "53.3", delta="-2.1")

    st.subheader("立即行動建議（2026年4月）")
    st.info("""
    - 將 60–80% 資金調整至**品質/自由現金流/高股息**風格
    - 集中布局**金融類**與**電信與公用事業**板塊
    - 目標安全邊際 20%（請使用「選股與完整估值」頁面取得 MOS 價格）
    - 本季 WACC 已加入 **+150 bps 景氣懲罰溢價**
    """)

    st.subheader("風險矩陣")
    st.table(pd.DataFrame({
        "風險項目":   ["景氣轉折", "地緣政治", "通膨急升", "流動性"],
        "發生機率":   ["中等", "高", "中高", "中等"],
        "對應措施":   ["每季 PMI 檢核", "WACC +150 bps 緩衝",
                       "WACC +150 bps 景氣懲罰", "聚焦大型權值股"],
    }))

    st.subheader("歷史季度績效（示意）")
    st.dataframe(df_hist, use_container_width=True)
    fig = px.bar(df_hist, x='季度', y=['IMFS報酬_%', '加權指數報酬_%'],
                 title="IMFS v2.4 vs 加權指數報酬率（%）", barmode='group')
    st.plotly_chart(fig, use_container_width=True)

# ====================== 選股與完整估值 ======================
elif page == "🏷️ 選股與完整估值":
    st.header("台股選股 & 完整 IMFS 估值")
    st.write("輸入股票代號或公司名稱搜尋，選取後執行完整業主盈餘 DCF 估值（含景氣調整 WACC）。")

    all_stocks = [
        {"ticker": t, "short": s, "full": f, "sector": sec,
         "display": f"{t} — {f}  [{sec}]"}
        for sec, stocks in TAIWAN_STOCK_UNIVERSE.items()
        for t, s, f in stocks
    ]

    search = st.text_input("搜尋股票代號或名稱（例：2330、台積電、金融）", "")
    q = search.strip().lower()
    filtered = (
        [x for x in all_stocks
         if q in x["ticker"] or q in x["full"].lower()
         or q in x["short"].lower() or q in x["sector"].lower()]
        if q else all_stocks
    )

    if not filtered:
        st.warning("查無符合結果。")
    else:
        chosen_display = st.selectbox(
            f"共 {len(filtered)} 筆結果，請選擇：",
            [x["display"] for x in filtered],
        )
        chosen = next(x for x in filtered if x["display"] == chosen_display)

        ca, cb, cc = st.columns(3)
        ca.markdown(f"**股票代號：** `{chosen['ticker']}.TW`")
        cb.markdown(f"**板塊：** {chosen['sector']}")
        cc.markdown(
            f"**景氣適配：** {'✅ 符合' if chosen['sector'] in current_sectors else '⚠️ 不符合'}"
        )

        if st.button("執行完整 IMFS 估值", type="primary"):
            run_full_imfs_valuation(chosen["ticker"], chosen["full"], chosen["sector"])

# ====================== 快速查詢 ======================
elif page == "🔍 快速查詢":
    st.header("股票快速查詢")
    ticker_input = st.text_input("輸入上市/上櫃代號（例：2881、2330）", "2881")
    if st.button("查詢"):
        info = fetch_stock_info(ticker_input)
        if info:
            _, full, _ = TICKER_LOOKUP.get(ticker_input, ("", ticker_input, "未知"))
            st.write(f"**公司名稱：** {info.get('longName', full)}")
            st.write(f"**目前股價：** NT${info.get('currentPrice', 'N/A')}")
            st.write(f"**本益比 P/E：** {info.get('trailingPE', 'N/A')}")
            st.write(f"**股價淨值比 P/B：** {info.get('priceToBook', 'N/A')}")
            st.write(f"**股息殖利率：** {(info.get('dividendYield') or 0)*100:.2f}%")
        else:
            st.error("無法取得資料，請確認代號。")

# ====================== 動態股票掃描 ======================
elif page == "🎯 動態股票掃描":
    st.header("動態市場掃描 — 景氣感知選股")

    col1, col2 = st.columns([2, 1])
    with col1:
        selected_sectors = st.multiselect(
            "選擇掃描板塊",
            options=list(TAIWAN_STOCK_UNIVERSE.keys()),
            default=current_sectors,
        )
    with col2:
        scan_button = st.button("立即掃描", type="primary")

    if selected_sectors and scan_button:
        pe_t, pb_t, dy_min = (12, 1.0, 0.03) if "品質" in current_bias else (18, 1.5, 0.02)
        with st.spinner("掃描台灣市場中..."):
            results = MarketScanner(selected_sectors).scan(pe_t, pb_t, dy_min)

        if not results.empty:
            st.success(f"找到 {len(results)} 檔候選標的。")
            st.dataframe(results, use_container_width=True)
            st.plotly_chart(
                px.bar(
                    results.groupby('板塊').size().reset_index(name='數量'),
                    x='板塊', y='數量', color='數量', title="各板塊候選數量",
                ),
                use_container_width=True,
            )
        else:
            st.warning("目前門檻條件下無符合標的。")

# ====================== 投資組合模擬 ======================
elif page == "📈 投資組合模擬":
    st.header("投資組合回測模擬器")

    col1, col2 = st.columns(2)
    with col1:
        backtest_years = st.slider("回測期間（年）", 1, 5, 3)
    with col2:
        strategy = st.selectbox("選擇策略", [
            "成長型（2330、2308、3231）",
            "品質/高股息（2881、2412、2882）",
            "均衡配置（2330、2881、2308）",
        ])

    strategy_map = {
        "成長型（2330、2308、3231）":       (["2330","2308","3231"], np.array([0.40,0.35,0.25]), "成長型"),
        "品質/高股息（2881、2412、2882）":  (["2881","2412","2882"], np.array([0.40,0.35,0.25]), "品質/高股息"),
        "均衡配置（2330、2881、2308）":     (["2330","2881","2308"], np.array([0.33,0.33,0.34]), "均衡配置"),
    }
    tickers, weights, name = strategy_map[strategy]

    end_dt   = datetime.now()
    start_dt = end_dt - timedelta(days=365 * backtest_years)
    st.info(f"回測 **{name}** 策略：{start_dt.date()} 至 {end_dt.date()}")

    with st.spinner("下載歷史價格資料..."):
        prices = download_historical_data(tuple(tickers), start_dt, end_dt)

    if prices:
        cum_ret, daily_ret = calculate_portfolio_returns(prices, weights)
        if cum_ret is not None and len(cum_ret) > 0:
            total_ret = cum_ret.iloc[-1] * 100
            ann_ret   = ((1 + cum_ret.iloc[-1]) ** (1 / backtest_years) - 1) * 100
            vol       = daily_ret.std() * np.sqrt(252) * 100
            sharpe    = (ann_ret - 2.0) / vol if vol > 0 else 0
            max_dd    = (cum_ret.cummax() - cum_ret).max() * 100

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("總報酬",       f"{total_ret:.1f}%")
            c2.metric("年化報酬",     f"{ann_ret:.1f}%")
            c3.metric("年化波動率",   f"{vol:.1f}%")
            c4.metric("夏普比率",     f"{sharpe:.2f}")
            c5.metric("最大回撤",     f"-{max_dd:.1f}%")

            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(
                x=cum_ret.index, y=cum_ret.values * 100,
                mode='lines', name=name, fill='tozeroy',
            ))
            fig3.update_layout(
                title=f"{name} — 累積報酬率（%）",
                xaxis_title="日期", yaxis_title="累積報酬 (%)", height=400
            )
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.warning("計算報酬時發生問題，請稍後再試。")
    else:
        st.warning("無法下載價格資料，請確認網路連線。")

# ====================== 觀察清單 ======================
elif page == "📋 觀察清單":
    st.header("觀察清單")
    wl = st.session_state.get("watchlist", [])
    if wl:
        st.dataframe(pd.DataFrame(wl), use_container_width=True)
        if st.button("清空觀察清單"):
            st.session_state["watchlist"] = []
            st.rerun()
    else:
        st.info("觀察清單目前為空。請至「選股與完整估值」頁面執行估值後加入。")

# ====================== 方法論說明 ======================
elif page == "📖 方法論說明":
    st.header("IMFS v2.4 方法論說明")
    st.write("本系統整合三大框架：景氣輪動（Investment Clock）、業主盈餘 DCF 估值、法醫會計評分。")

    st.markdown("---")

    st.subheader("一、景氣輪動（Investment Clock）")
    st.markdown("""
**原理：**
Investment Clock 由美林證券（Merrill Lynch）於 2004 年提出，將經濟循環分為四個象限：

| 象限 | 景氣 | 通膨 | 偏好板塊 |
|------|------|------|----------|
| 復甦期（Reflation） | ↑ 回升 | ↓ 低 | 景氣循環股、消費股 |
| 擴張期（Expansion） | ↑ 高 | ↑ 升 | 科技、原材料 |
| 過熱期（Overheat） | → 高原 | ↑ 高 | 能源、商品、高股息 |
| 滯脹期（Stagflation） | ↓ 降 | ↑ 高 | 公用事業、防禦型金融 |

**本系統應用：**
- 每季根據 PMI、CPI、GDP 缺口判斷當前象限
- 依象限決定**偏好板塊**與**WACC 懲罰溢價**
- 當前（2026 Q2）：溫和擴張轉過熱 → 偏好金融、電信，WACC 加罰 150 bps

**參考來源：**
- Merrill Lynch Investment Clock (2004)
- Fidelity Sector Rotation Framework
    """)

    st.markdown("---")

    st.subheader("二、業主盈餘 DCF 估值")
    st.markdown("""
**業主盈餘（Owner Earnings）**
由 Warren Buffett 在 1986 年波克夏年報中提出，定義為企業實際可供股東運用的現金：

```
業主盈餘 = 淨利 + 折舊/攤銷 − 資本支出（維持性）
```

相較於帳面淨利，業主盈餘剔除了折舊帶來的非現金費用，並扣除維持競爭力所需的再投資，
更能反映企業真實的現金創造能力。

**折現率（WACC）組成：**

| 項目 | 數值 | 說明 |
|------|------|------|
| 無風險利率 Rf | 1.5% | 台灣10年期公債殖利率 |
| Beta × 股權風險溢價 | Beta × 5.5% | 系統性風險補償 |
| 地緣政治緩衝 | +1.5% | 台灣特有地緣政治風險（台海） |
| 景氣懲罰溢價 | +1.5%（過熱/滯脹時） | 景氣下行時增加折現率 |

**DCF 計算流程：**
1. 以業主盈餘每股為基礎現金流
2. 依 yfinance 成長率估計（上限 15%）成長 5 年
3. 第 5 年以永續成長率 2% 計算終值（Gordon Growth Model）
4. 以 WACC 折現回現值
5. **內在價值 × 80% = 安全邊際買進價（MOS Price）**

**參考來源：**
- Warren Buffett, Berkshire Hathaway Annual Report (1986)
- Aswath Damodaran, *Investment Valuation* (2012)
- Benjamin Graham, *The Intelligent Investor* (1949)
    """)

    st.markdown("---")

    st.subheader("三、法醫會計評分（Forensic Accounting）")
    st.markdown("""
**3.1 Piotroski F-Score（代理版）**

由 Joseph Piotroski（2000）提出，從獲利能力、槓桿/流動性、營運效率三個維度給分，
本系統使用 yfinance 可取得的資料進行代理計算（最高 7 分）：

| 指標 | 計分條件 |
|------|----------|
| ROE 股東權益報酬率 | > 0 |
| ROA 資產報酬率 | > 0 |
| 營業現金流 | > 0 |
| 現金流品質 | 營業現金流 > 淨利（低應計） |
| 負債比 | 負債/權益 < 100% |
| 流動比率 | > 1.0 |
| 盈餘成長 | earningsGrowth > 0 |

解讀：5–7 分 = 強健；3–4 分 = 普通；< 3 分 = 偏弱

---

**3.2 Beneish M-Score（應計項目代理）**

由 Messod Beneish（1999）提出，用於偵測盈餘操縱。
本系統使用應計項目比率作為代理：

```
應計比率 = （淨利 − 營業現金流）/ |淨利|
```
若 > 0.5，表示獲利高度依賴應計項目而非實際現金，標記為**疑似盈餘虛增**。

---

**3.3 Altman Z-Score（代理版）**

由 Edward Altman（1968）提出，預測企業財務危機。
本系統使用可得資料的簡化代理：

```
Z 代理 = ROE × 2 + 流動比率 × 0.5 + P/B × 0.3
```
解讀：< 1.5 = 危機區；1.5–3.0 = 灰色地帶；> 3.0 = 安全區

**參考來源：**
- Piotroski, J.D. (2000), *Journal of Accounting Research*
- Beneish, M.D. (1999), *Financial Analysts Journal*
- Altman, E.I. (1968), *Journal of Finance*
    """)

    st.markdown("---")

    st.subheader("四、系統整合邏輯（如何使用）")
    st.markdown("""
**步驟一：確認景氣象限**
→ 查看「主儀表板」的景氣狀態與當前偏好板塊

**步驟二：掃描候選標的**
→ 使用「動態股票掃描」在偏好板塊中篩選低本益比/低淨值比/高殖利率個股

**步驟三：個股深度估值**
→ 使用「選股與完整估值」執行 DCF，取得內在價值與安全邊際價

**步驟四：法醫財務篩選**
→ 確認 Piotroski ≥ 3、無 Beneish 警示、Altman Z 非危機區

**步驟五：景氣適配確認**
→ 確認個股板塊符合當前景氣偏好

**步驟六：買進條件**
→ 股價 ≤ 安全邊際價（內在價值 × 80%）+ 符合景氣偏好 + Piotroski ≥ 3

**步驟七：持倉管理**
→ 股價超越內在價值時考慮減碼；每季更新景氣判斷並重新掃描
    """)

    st.markdown("---")
    st.caption("IMFS v2.4 | 參考文獻：Buffett (1986)、Damodaran (2012)、Graham (1949)、Piotroski (2000)、Beneish (1999)、Altman (1968)、Merrill Lynch Investment Clock (2004)")

st.markdown("---")
st.caption("IMFS v2.4 | 業主盈餘 · 景氣調整 WACC · 法醫會計評分 · 台灣市場專用")
