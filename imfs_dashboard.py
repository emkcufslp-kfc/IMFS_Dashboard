# =====================================================
# IMFS v2.5 – 機構級台股輪動儀表板（繁體中文版）
# 修正殖利率計算 + 全面 UI 重設計
# =====================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np

st.set_page_config(page_title="IMFS v2.5 台股儀表板", layout="wide", initial_sidebar_state="expanded")

# ── 全域樣式 ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* 全域字型 */
html, body, [class*="css"] { font-family: "Noto Sans TC", "Microsoft JhengHei", sans-serif; }

/* 頁面背景 */
.main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1400px; }

/* 區塊卡片 */
.card {
    background: #1e2130;
    border: 1px solid #2d3250;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
}
.card-title {
    font-size: 0.78rem;
    font-weight: 600;
    color: #8b92a8;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.3rem;
}
.card-value {
    font-size: 1.6rem;
    font-weight: 700;
    color: #e8eaf0;
}
.card-sub { font-size: 0.82rem; color: #8b92a8; margin-top: 0.2rem; }

/* 訊號徽章 */
.badge-buy    { background:#0d3b26; color:#34d399; border:1px solid #34d399;
                padding:3px 10px; border-radius:20px; font-weight:700; font-size:0.85rem; }
.badge-hold   { background:#3b2e0d; color:#fbbf24; border:1px solid #fbbf24;
                padding:3px 10px; border-radius:20px; font-weight:700; font-size:0.85rem; }
.badge-avoid  { background:#3b0d0d; color:#f87171; border:1px solid #f87171;
                padding:3px 10px; border-radius:20px; font-weight:700; font-size:0.85rem; }

/* 分隔線 */
.section-divider { border: none; border-top: 1px solid #2d3250; margin: 1.5rem 0; }

/* 側邊欄 */
[data-testid="stSidebar"] { background: #131623; border-right: 1px solid #2d3250; }
[data-testid="stSidebar"] .stSelectbox label { color: #8b92a8; font-size: 0.8rem; }

/* 指標覆寫 */
[data-testid="stMetricValue"] { font-size: 1.25rem !important; }
[data-testid="stMetricLabel"] { font-size: 0.75rem !important; color: #8b92a8 !important; }
</style>
""", unsafe_allow_html=True)

# ====================== 參數設定 ======================
class IMFS_Config:
    REGIME_PENALTY  = 150   # bps — 過熱/滯脹時加入 WACC
    ERP             = 5.5   # 股權風險溢價 %
    GEO_BUFFER      = 150   # 台灣地緣政治緩衝 bps
    TRANS_COST      = 0.003 # 交易成本 0.3%
    MOS             = 0.20  # 安全邊際 20%
    RF              = 0.015 # 台灣10年期無風險利率 ~1.5%
    TAX_RATE        = 0.20  # 台灣企業所得稅 20%
    TERMINAL_GROWTH = 0.02  # DCF 永續成長率

# ====================== 台股標的 ======================
TAIWAN_STOCK_UNIVERSE = {
    '科技類': [
        ('2330', 'TSMC',   '台灣積體電路製造'),
        ('2317', '鴻海',   '鴻海精密工業'),
        ('2454', '聯發科', '聯發科技'),
        ('2308', '台達電', '台達電子工業'),
        ('2382', '廣達',   '廣達電腦'),
        ('3231', '緯創',   '緯創資通'),
        ('2353', '宏碁',   '宏碁股份有限公司'),
        ('2303', '聯電',   '聯華電子'),
        ('2409', '友達',   '友達光電'),
        ('3034', '聯詠',   '聯詠科技'),
        ('2379', '瑞昱',   '瑞昱半導體'),
        ('2344', '華邦電', '華邦電子'),
        ('2357', '英業達', '英業達股份有限公司'),
        ('2376', '技嘉',   '技嘉科技'),
        ('3711', '創意',   '創意電子'),
    ],
    '金融類': [
        ('2881', '富邦金', '富邦金融控股'),
        ('2882', '國泰金', '國泰金融控股'),
        ('2884', '玉山金', '玉山金融控股'),
        ('2885', '元大金', '元大金融控股'),
        ('2886', '兆豐金', '兆豐金融控股'),
        ('2887', '台新金', '台新金融控股'),
        ('2888', '新光金', '新光金融控股'),
        ('2890', '永豐金', '永豐金融控股'),
        ('2891', '中信金', '中國信託金融控股'),
        ('2892', '第一金', '第一金融控股'),
        ('5876', '上海商銀','上海商業儲蓄銀行'),
    ],
    '電信與公用事業': [
        ('2412', '中華電', '中華電信'),
        ('4904', '遠傳',   '遠傳電信'),
        ('3045', '台灣大', '台灣大哥大'),
        ('6505', '台塑化', '台灣塑膠化學工業'),
        ('9945', '潤泰全', '潤泰全球'),
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
        ('2912', '統一超', '統一超商（7-ELEVEN）'),
        ('1216', '統一',   '統一企業'),
        ('2207', '和泰車', '和泰汽車'),
        ('2103', '亞泥',   '亞洲水泥'),
        ('9910', '豐泰',   '豐泰企業'),
        ('6239', '力成',   '力成科技'),
    ],
}

TICKER_LOOKUP: dict[str, tuple[str, str, str]] = {
    t: (s, f, sec)
    for sec, stocks in TAIWAN_STOCK_UNIVERSE.items()
    for t, s, f in stocks
}

# ====================== 景氣狀態 ======================
current_regime  = "溫和擴張（過熱/滯脹傾向）"
current_bias    = "品質、低波動、自由現金流／股息殖利率"
current_sectors = ["金融類", "電信與公用事業"]

historical_data = {
    '季度':          ['2023 Q1-Q2','2023 Q3-Q4','2024 Q1-Q2','2024 Q3-Q4','2025 Q1-Q2','2025 Q3-Q4','2026 Q1'],
    '景氣狀態':      ['擴張','擴張','擴張','擴張','溫和擴張/品質','溫和擴張/品質','溫和擴張/過熱'],
    '因子偏好':      ['成長','成長','成長','成長','品質/自由現金流','品質/自由現金流','品質/自由現金流'],
    'IMFS報酬_%':    [29.0, 26.5, 21.0, 18.5, 21.0, 14.5, 11.0],
    '加權指數報酬_%': [21.0, 23.5, 17.5, 14.5, 23.5, 13.0, 22.0],
}
df_hist = pd.DataFrame(historical_data)

# ====================== 工具函數 ======================

def _is_overheat() -> bool:
    return any(k in current_regime for k in ("過熱", "滯脹"))


def _norm_div_yield(raw) -> float:
    """
    yfinance 對台股的 dividendYield 回傳值不一致：
    部分回傳小數（0.035 = 3.5%），部分回傳百分比整數（3.5 = 3.5%）。
    統一轉換為百分比顯示值（例：3.50）。
    判斷規則：若原始值 > 1，視為已是百分比形式，直接使用；否則乘以 100。
    """
    if raw is None:
        return 0.0
    v = float(raw)
    return v if v > 1.0 else v * 100.0


@st.cache_data(ttl=300)
def fetch_info(ticker: str) -> dict:
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
def download_prices(tickers: tuple, start, end) -> dict:
    data = {}
    for t in tickers:
        try:
            hist = yf.download(t + ".TW", start=start, end=end,
                               progress=False, auto_adjust=True)
            if hist.empty:
                continue
            close = hist["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            s = close.squeeze()
            if isinstance(s, pd.Series) and not s.empty:
                data[t] = s
        except Exception:
            pass
    return data


def _cf_row(cf: pd.DataFrame, *keys) -> float:
    for k in keys:
        if k in cf.index:
            v = cf.loc[k].iloc[0]
            return float(v) if pd.notna(v) else 0.0
    return 0.0


def _signal_badge(signal: str) -> str:
    if "買進" in signal:
        return f'<span class="badge-buy">{signal}</span>'
    if "持有" in signal:
        return f'<span class="badge-hold">{signal}</span>'
    return f'<span class="badge-avoid">{signal}</span>'


# ====================== 完整估值 ======================

def run_valuation(ticker: str, company: str, sector: str):
    st.markdown(f"### {ticker} — {company}")
    st.caption(f"板塊：{sector}　｜　景氣適配：{'✅ 符合' if sector in current_sectors else '⚠️ 不符合'}")

    with st.spinner("從 Yahoo Finance 取得資料…"):
        info = fetch_info(ticker)
        cf   = fetch_cashflow(ticker)

    if not info:
        st.error("無法取得資料，請確認股票代號後再試。")
        return

    price   = float(info.get('currentPrice') or info.get('regularMarketPrice') or 0)
    shares  = float(info.get('sharesOutstanding') or 1)
    beta    = float(info.get('beta') or 1.0)
    mktcap  = float(info.get('marketCap') or price * shares)
    debt    = float(info.get('totalDebt') or 0)

    # 業主盈餘
    if not cf.empty:
        ni    = _cf_row(cf, 'Net Income', 'NetIncome')
        da    = _cf_row(cf, 'Depreciation And Amortization',
                            'Reconciled Depreciation', 'DepreciationAndAmortization')
        capex = abs(_cf_row(cf, 'Capital Expenditure', 'CapitalExpenditures',
                                'Purchase Of Property Plant And Equipment'))
        oe    = ni + da - capex
    else:
        ni = da = capex = 0.0
        oe = float(info.get('freeCashflow') or 0)
    oe_ps = oe / shares if shares > 0 else 0.0

    # WACC
    rf        = IMFS_Config.RF
    geo       = IMFS_Config.GEO_BUFFER / 10_000
    reg_pen   = IMFS_Config.REGIME_PENALTY / 10_000 if _is_overheat() else 0.0
    coe       = rf + beta * (IMFS_Config.ERP / 100) + geo + reg_pen
    tot_cap   = mktcap + debt
    ew        = mktcap / tot_cap if tot_cap > 0 else 1.0
    int_exp   = abs(float(info.get('interestExpense') or 0))
    cod       = (int_exp / debt) if debt > 0 and int_exp > 0 else 0.03
    wacc      = ew * coe + (1 - ew) * cod * (1 - IMFS_Config.TAX_RATE)

    # 5年 DCF
    g5   = max(0.0, min(float(info.get('earningsGrowth') or info.get('revenueGrowth') or 0.05), 0.15))
    tg   = IMFS_Config.TERMINAL_GROWTH
    pv5  = sum(oe_ps * (1 + g5)**yr / (1 + wacc)**yr for yr in range(1, 6))
    tv   = (oe_ps * (1 + g5)**5 * (1 + tg) / (wacc - tg)) if wacc > tg else 0.0
    tv_pv = tv / (1 + wacc)**5
    iv    = pv5 + tv_pv
    mos   = iv * (1 - IMFS_Config.MOS)
    upside = ((iv - price) / price * 100) if price > 0 else 0.0

    # 訊號
    if price > 0 and price <= mos:
        signal = "買進 — 低於安全邊際價"
    elif price > 0 and price <= iv:
        signal = "持有 — 低於內在價值"
    else:
        signal = "觀望 — 高於內在價值"

    # 財務指標
    roe   = float(info.get('returnOnEquity') or 0)
    roa   = float(info.get('returnOnAssets') or 0)
    de    = float(info.get('debtToEquity') or 0)
    cr    = float(info.get('currentRatio') or 0)
    ocf   = float(info.get('operatingCashflow') or 0)
    ni_i  = float(info.get('netIncomeToCommon') or 0)
    pb    = float(info.get('priceToBook') or 0)
    dy    = _norm_div_yield(info.get('dividendYield'))

    pf = sum([roe > 0, roa > 0, ocf > 0, ocf > ni_i, de < 100, cr > 1.0,
              float(info.get('earningsGrowth') or 0) > 0])
    pf_lbl = "強健" if pf >= 5 else "普通" if pf >= 3 else "偏弱"
    ben    = "⚠️ 疑似盈餘虛增" if (ni_i - ocf) / max(abs(ni_i), 1) > 0.5 else "✅ 正常"
    z      = roe * 2 + cr * 0.5 + pb * 0.3
    z_lbl  = "⚠️ 危機" if z < 1.5 else "🟡 灰色" if z < 3 else "✅ 安全"

    # ── 頂部摘要列 ──────────────────────────────────────────────
    st.markdown(f"**投資訊號：** {_signal_badge(signal)}", unsafe_allow_html=True)
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("目前股價",          f"NT${price:,.1f}"  if price else "—")
    c2.metric("內在價值（DCF）",   f"NT${iv:,.1f}"     if iv    else "—")
    c3.metric("安全邊際價（-20%）",f"NT${mos:,.1f}"    if mos   else "—")
    c4.metric("距內在價值漲幅",    f"{upside:+.1f}%"   if price else "—")
    c5.metric("WACC",              f"{wacc*100:.2f}%")
    c6.metric("股息殖利率",        f"{dy:.2f}%")

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ── WACC 與 DCF 並排 ────────────────────────────────────────
    left, right = st.columns(2)

    with left:
        st.markdown("#### WACC 拆解")
        wacc_df = pd.DataFrame({
            "組成": ["無風險利率 Rf", "Beta × ERP", "地緣政治緩衝", "景氣懲罰", "股權成本", "WACC（加權）"],
            "%":   [rf*100, beta*(IMFS_Config.ERP), IMFS_Config.GEO_BUFFER/100,
                    IMFS_Config.REGIME_PENALTY/100 if _is_overheat() else 0,
                    coe*100, wacc*100],
        })
        fig_wacc = px.bar(wacc_df, x="組成", y="%", text_auto=".2f",
                          color="組成", title="WACC 組成（%）",
                          color_discrete_sequence=px.colors.sequential.Blues_r)
        fig_wacc.update_layout(showlegend=False, height=300,
                                plot_bgcolor="#1e2130", paper_bgcolor="#1e2130",
                                font_color="#c8ccd8", title_font_size=13)
        st.plotly_chart(fig_wacc, use_container_width=True)

    with right:
        st.markdown("#### DCF 估值拆解")
        dcf_df = pd.DataFrame({
            "項目": ["5年現金流現值", "永續價值現值", "內在價值", "安全邊際價"],
            "NT$":  [pv5, tv_pv, iv, mos],
        })
        fig_dcf = px.bar(dcf_df, x="項目", y="NT$", text_auto=".1f",
                         color="項目", title="DCF 組成（NT$ / 股）",
                         color_discrete_sequence=["#4f86c6","#2563eb","#1d4ed8","#f59e0b"])
        if price:
            fig_dcf.add_hline(y=price, line_dash="dot", line_color="#f87171",
                              annotation_text=f"現價 {price:.1f}",
                              annotation_font_color="#f87171")
        fig_dcf.update_layout(showlegend=False, height=300,
                               plot_bgcolor="#1e2130", paper_bgcolor="#1e2130",
                               font_color="#c8ccd8", title_font_size=13)
        st.plotly_chart(fig_dcf, use_container_width=True)

    # ── 業主盈餘 ────────────────────────────────────────────────
    st.markdown("#### 業主盈餘（Owner Earnings）")
    oe_c1, oe_c2, oe_c3, oe_c4 = st.columns(4)
    if not cf.empty:
        oe_c1.metric("淨利",       f"NT${ni/1e9:.2f}B")
        oe_c2.metric("折舊＋攤銷", f"NT${da/1e9:.2f}B")
        oe_c3.metric("資本支出",   f"NT${capex/1e9:.2f}B")
        oe_c4.metric("業主盈餘",   f"NT${oe/1e9:.2f}B")
    else:
        oe_c1.metric("自由現金流（替代）", f"NT${oe/1e9:.2f}B")
        st.caption("現金流量表資料不足，以自由現金流替代計算")

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ── 法醫評分 ────────────────────────────────────────────────
    st.markdown("#### 財務健全度（法醫會計）")
    fa1, fa2, fa3 = st.columns(3)
    fa1.metric("Piotroski F-Score", f"{pf}/7 — {pf_lbl}",
               help="7項財務健全指標：獲利、現金流品質、槓桿、流動性、成長")
    fa2.metric("Beneish 應計項目",  ben,
               help="應計比率 >0.5 時標記疑似盈餘虛增")
    fa3.metric("Altman Z（代理）",  z_lbl,
               help="<1.5 危機區 | 1.5-3 灰色 | >3 安全")

    fin_df = pd.DataFrame({
        "指標":["ROE","ROA","負債/權益","流動比率","P/B","股息殖利率"],
        "數值":[f"{roe*100:.1f}%" if roe else "—",
                f"{roa*100:.1f}%" if roa else "—",
                f"{de:.1f}%"      if de   else "—",
                f"{cr:.2f}"       if cr   else "—",
                f"{pb:.2f}"       if pb   else "—",
                f"{dy:.2f}%"],
    })
    st.dataframe(fin_df, use_container_width=True, hide_index=True,
                 column_config={"指標": st.column_config.TextColumn(width="medium"),
                                "數值": st.column_config.TextColumn(width="medium")})

    # ── 加入觀察清單 ────────────────────────────────────────────
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
    if st.button(f"➕ 加入觀察清單：{ticker}", type="secondary"):
        wl = st.session_state.get("watchlist", [])
        entry = {"代號": ticker, "公司": company, "板塊": sector, "股價": price,
                 "內在價值": round(iv, 1), "MOS價": round(mos, 1),
                 "訊號": signal, "Piotroski": f"{pf}/7", "殖利率%": f"{dy:.2f}%"}
        if ticker not in [w["代號"] for w in wl]:
            wl.append(entry)
            st.session_state["watchlist"] = wl
            st.success(f"✅ {ticker} 已加入觀察清單")
        else:
            st.info(f"{ticker} 已在觀察清單中")


# ====================== 掃描器 ======================

class MarketScanner:
    def __init__(self, sectors):
        self.sectors = sectors

    @st.cache_data(ttl=600)
    def _scan(_self, sectors_t, pe_thr, pb_thr, dy_min):
        rows = []
        for sec in sectors_t:
            for tkr, short, full in TAIWAN_STOCK_UNIVERSE.get(sec, []):
                try:
                    info  = yf.Ticker(tkr + ".TW").info
                    pe    = float(info.get('trailingPE') or float('inf'))
                    pb    = float(info.get('priceToBook') or float('inf'))
                    dy    = _norm_div_yield(info.get('dividendYield'))
                    price = float(info.get('currentPrice') or 0)
                    mc    = float(info.get('marketCap') or 0)
                    score = int(pe < pe_thr) + int(pb < pb_thr) + int(dy > dy_min)
                    if score >= 1:
                        rows.append({
                            '代號':     tkr,
                            '公司名稱': full,
                            '板塊':     sec,
                            '股價':     round(price, 2),
                            'P/E':      round(pe, 2)  if pe != float('inf') else None,
                            'P/B':      round(pb, 2)  if pb != float('inf') else None,
                            '殖利率%':  round(dy, 2),
                            '市值(十億)':round(mc/1e9, 2) if mc else None,
                            '評分':     score,
                        })
                except Exception:
                    continue
        rows.sort(key=lambda x: x['評分'], reverse=True)
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    def scan(self, pe=15, pb=1.2, dy=0.02):
        return self._scan(tuple(self.sectors), pe, pb, dy)


# ====================== 投組回測 ======================

def calc_returns(prices: dict, weights: np.ndarray):
    clean = {k: (v.squeeze() if hasattr(v,'squeeze') else v)
             for k, v in prices.items()
             if isinstance(v.squeeze() if hasattr(v,'squeeze') else v, pd.Series)}
    if not clean:
        return None, None
    df = pd.DataFrame(clean).dropna()
    if df.empty:
        return None, None
    w = weights[:df.shape[1]]
    w = w / w.sum()
    ret  = df.pct_change().fillna(0)
    pret = (ret * w).sum(axis=1)
    cum  = (1 + pret).cumprod() - 1
    return cum, pret


# ====================== 側邊欄導覽 ======================
with st.sidebar:
    st.markdown("## IMFS v2.5")
    st.markdown("**台股機構級輪動系統**")
    st.markdown("---")
    page = st.radio("功能選單", [
        "📊 主儀表板",
        "🏷️ 選股與完整估值",
        "🔍 快速查詢",
        "🎯 動態股票掃描",
        "📈 投資組合模擬",
        "📋 觀察清單",
        "📖 方法論說明",
    ], label_visibility="collapsed")
    st.markdown("---")
    st.caption(f"當前景氣：**{current_regime}**")
    st.caption(f"偏好板塊：{'、'.join(current_sectors)}")

# ====================== 主儀表板 ======================
if page == "📊 主儀表板":
    st.markdown("# 主儀表板")
    st.caption("景氣輪動狀態 ｜ 即時行動建議 ｜ 歷史績效")

    # KPI 列
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("景氣狀態",       current_regime)
    k2.metric("偏好板塊",       "、".join(current_sectors))
    k3.metric("台灣 PMI（3月）","53.3", delta="-2.1")
    k4.metric("WACC 景氣加罰",  "+150 bps（過熱）")

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    left, right = st.columns([1, 1])
    with left:
        st.markdown("#### 立即行動建議（2026 Q2）")
        st.info("""
- 60–80% 資金布局**品質/自由現金流/高股息**
- 聚焦**金融類**與**電信與公用事業**
- 目標安全邊際 20%（使用選股估值取得 MOS 價格）
- 本季 WACC 已加入 **+150 bps 景氣懲罰溢價**
        """)

    with right:
        st.markdown("#### 風險矩陣")
        risk_df = pd.DataFrame({
            "風險":   ["景氣轉折","地緣政治","通膨急升","流動性"],
            "機率":   ["中等","高","中高","中等"],
            "對應":   ["+PMI 季檢","WACC +1.5%","WACC +1.5% 懲罰","聚焦大型股"],
        })
        st.dataframe(risk_df, use_container_width=True, hide_index=True)

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
    st.markdown("#### 歷史季度績效（示意）")

    tab1, tab2 = st.tabs(["圖表", "數據表"])
    with tab1:
        fig = px.bar(df_hist, x='季度', y=['IMFS報酬_%','加權指數報酬_%'],
                     barmode='group', title="IMFS v2.5 vs 加權指數報酬率（%）",
                     color_discrete_map={'IMFS報酬_%':'#3b82f6','加權指數報酬_%':'#6b7280'})
        fig.update_layout(plot_bgcolor="#1e2130", paper_bgcolor="#1e2130",
                          font_color="#c8ccd8", legend_title_text="")
        st.plotly_chart(fig, use_container_width=True)
    with tab2:
        st.dataframe(df_hist, use_container_width=True, hide_index=True)

# ====================== 選股與完整估值 ======================
elif page == "🏷️ 選股與完整估值":
    st.markdown("# 選股與完整 IMFS 估值")
    st.caption("搜尋台股代號或公司名稱，執行業主盈餘 DCF 估值（含景氣調整 WACC）")

    all_stocks = [
        {"t": t, "s": s, "f": f, "sec": sec,
         "disp": f"{t} — {f}  [{sec}]"}
        for sec, stk in TAIWAN_STOCK_UNIVERSE.items()
        for t, s, f in stk
    ]

    search = st.text_input("🔍 搜尋代號或名稱（例：2330、台積電、金融）", "",
                            placeholder="輸入代號或名稱…")
    q = search.strip().lower()
    filtered = [x for x in all_stocks if q in x["t"] or q in x["f"].lower()
                or q in x["s"].lower() or q in x["sec"].lower()] if q else all_stocks

    if not filtered:
        st.warning("查無符合結果。")
    else:
        chosen_disp = st.selectbox(f"共 {len(filtered)} 筆，請選擇：",
                                   [x["disp"] for x in filtered])
        chosen = next(x for x in filtered if x["disp"] == chosen_disp)

        ca, cb, cc = st.columns(3)
        ca.info(f"**代號：** `{chosen['t']}.TW`")
        cb.info(f"**板塊：** {chosen['sec']}")
        cc.info(f"**景氣適配：** {'✅ 符合' if chosen['sec'] in current_sectors else '⚠️ 不符合'}")

        if st.button("執行完整 IMFS 估值 ▶", type="primary", use_container_width=True):
            run_valuation(chosen["t"], chosen["f"], chosen["sec"])

# ====================== 快速查詢 ======================
elif page == "🔍 快速查詢":
    st.markdown("# 股票快速查詢")
    col1, col2 = st.columns([3, 1])
    with col1:
        ticker_input = st.text_input("上市/上櫃代號", "2881", placeholder="例：2881")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        fetch_btn = st.button("查詢", type="primary", use_container_width=True)

    if fetch_btn:
        info = fetch_info(ticker_input)
        if info:
            _, full, _ = TICKER_LOOKUP.get(ticker_input, ("","",""))
            dy = _norm_div_yield(info.get('dividendYield'))
            r1, r2, r3, r4, r5 = st.columns(5)
            r1.metric("公司",     info.get('longName', full) or full)
            r2.metric("股價",     f"NT${info.get('currentPrice','—')}")
            r3.metric("P/E",      f"{info.get('trailingPE','—')}")
            r4.metric("P/B",      f"{info.get('priceToBook','—')}")
            r5.metric("殖利率",   f"{dy:.2f}%")
        else:
            st.error("無法取得資料，請確認代號。")

# ====================== 動態掃描 ======================
elif page == "🎯 動態股票掃描":
    st.markdown("# 動態市場掃描")
    st.caption("景氣感知篩選：依當前偏好板塊自動調整門檻")

    with st.expander("掃描設定", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            sel_sectors = st.multiselect("板塊", list(TAIWAN_STOCK_UNIVERSE.keys()),
                                         default=current_sectors)
        with col2:
            pe_thr = st.number_input("P/E 上限", value=12 if "品質" in current_bias else 18,
                                     min_value=1, max_value=50)
        with col3:
            pb_thr = st.number_input("P/B 上限", value=1.0 if "品質" in current_bias else 1.5,
                                     min_value=0.1, max_value=10.0, step=0.1)
        with col4:
            dy_min = st.number_input("殖利率下限 (%)", value=3.0 if "品質" in current_bias else 2.0,
                                     min_value=0.0, max_value=15.0, step=0.5)

    if sel_sectors and st.button("立即掃描", type="primary", use_container_width=True):
        with st.spinner("掃描台灣市場中…"):
            results = MarketScanner(sel_sectors).scan(pe_thr, pb_thr, dy_min / 100)

        if not results.empty:
            st.success(f"找到 **{len(results)}** 檔候選標的")

            # 評分圓餅圖 + 板塊分布
            ch1, ch2 = st.columns(2)
            with ch1:
                fig_s = px.pie(results, names='板塊', title="板塊分布",
                               color_discrete_sequence=px.colors.qualitative.Set2)
                fig_s.update_layout(plot_bgcolor="#1e2130", paper_bgcolor="#1e2130",
                                    font_color="#c8ccd8", height=260)
                st.plotly_chart(fig_s, use_container_width=True)
            with ch2:
                score_cnt = results['評分'].value_counts().reset_index()
                score_cnt.columns = ['評分', '數量']
                fig_sc = px.bar(score_cnt, x='評分', y='數量', title="評分分布",
                                color='數量', color_continuous_scale='Blues')
                fig_sc.update_layout(plot_bgcolor="#1e2130", paper_bgcolor="#1e2130",
                                     font_color="#c8ccd8", height=260)
                st.plotly_chart(fig_sc, use_container_width=True)

            # 結果表格（含 column_config）
            st.dataframe(
                results,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "代號":      st.column_config.TextColumn("代號",      width=70),
                    "公司名稱":  st.column_config.TextColumn("公司名稱",  width=160),
                    "板塊":      st.column_config.TextColumn("板塊",      width=120),
                    "股價":      st.column_config.NumberColumn("股價",     format="NT$%.2f"),
                    "P/E":       st.column_config.NumberColumn("P/E",      format="%.2f"),
                    "P/B":       st.column_config.NumberColumn("P/B",      format="%.2f"),
                    "殖利率%":   st.column_config.NumberColumn("殖利率 %", format="%.2f%%"),
                    "市值(十億)":st.column_config.NumberColumn("市值（十億）", format="%.1f"),
                    "評分":      st.column_config.ProgressColumn("評分", min_value=0, max_value=3),
                },
            )
        else:
            st.warning("目前門檻條件下無符合標的，請調整篩選條件。")

# ====================== 投資組合模擬 ======================
elif page == "📈 投資組合模擬":
    st.markdown("# 投資組合回測模擬器")

    with st.expander("策略設定", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            yrs = st.slider("回測期間（年）", 1, 5, 3)
        with col2:
            strat = st.selectbox("策略", [
                "成長型（2330、2308、3231）",
                "品質/高股息（2881、2412、2882）",
                "均衡配置（2330、2881、2308）",
            ])

    smap = {
        "成長型（2330、2308、3231）":       (["2330","2308","3231"], np.array([.40,.35,.25]), "成長型"),
        "品質/高股息（2881、2412、2882）":  (["2881","2412","2882"], np.array([.40,.35,.25]), "品質/高股息"),
        "均衡配置（2330、2881、2308）":     (["2330","2881","2308"], np.array([.33,.33,.34]), "均衡配置"),
    }
    tkrs, wts, name = smap[strat]
    end_dt, start_dt = datetime.now(), datetime.now() - timedelta(days=365*yrs)
    st.info(f"回測 **{name}** ｜ {start_dt.date()} → {end_dt.date()}")

    with st.spinner("下載歷史價格…"):
        prices = download_prices(tuple(tkrs), start_dt, end_dt)

    cum, dret = calc_returns(prices, wts)
    if cum is not None and len(cum) > 0:
        tr   = cum.iloc[-1] * 100
        ar   = ((1 + cum.iloc[-1])**(1/yrs) - 1) * 100
        vol  = dret.std() * np.sqrt(252) * 100
        shr  = (ar - 2.0) / vol if vol > 0 else 0
        mdd  = (cum.cummax() - cum).max() * 100

        m1,m2,m3,m4,m5 = st.columns(5)
        m1.metric("總報酬",     f"{tr:.1f}%")
        m2.metric("年化報酬",   f"{ar:.1f}%")
        m3.metric("年化波動率", f"{vol:.1f}%")
        m4.metric("夏普比率",   f"{shr:.2f}")
        m5.metric("最大回撤",   f"-{mdd:.1f}%")

        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=cum.index, y=cum.values*100,
                                   mode='lines', name=name,
                                   fill='tozeroy', line_color='#3b82f6'))
        fig3.add_hline(y=0, line_dash="dash", line_color="#6b7280")
        fig3.update_layout(title=f"{name} — 累積報酬率（%）",
                           xaxis_title="日期", yaxis_title="累積報酬 (%)",
                           height=420, plot_bgcolor="#1e2130",
                           paper_bgcolor="#1e2130", font_color="#c8ccd8")
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.warning("無法計算，部分標的資料不足，請確認網路或換用其他策略。")

# ====================== 觀察清單 ======================
elif page == "📋 觀察清單":
    st.markdown("# 觀察清單")
    wl = st.session_state.get("watchlist", [])
    if wl:
        st.dataframe(
            pd.DataFrame(wl), use_container_width=True, hide_index=True,
            column_config={
                "訊號": st.column_config.TextColumn("訊號", width=200),
                "殖利率%": st.column_config.TextColumn("殖利率"),
            }
        )
        if st.button("清空觀察清單", type="secondary"):
            st.session_state["watchlist"] = []
            st.rerun()
    else:
        st.info("觀察清單目前為空。請至「選股與完整估值」執行估值後加入。")

# ====================== 方法論說明 ======================
elif page == "📖 方法論說明":
    st.markdown("# 方法論說明")
    st.caption("IMFS v2.5 整合三大框架：景氣輪動 × 業主盈餘 DCF × 法醫會計評分")

    tab1, tab2, tab3, tab4 = st.tabs([
        "一、景氣輪動", "二、業主盈餘 DCF", "三、法醫會計", "四、使用流程"
    ])

    with tab1:
        st.markdown("""
### Investment Clock 景氣輪動

由美林證券（2004）提出，將經濟循環分為四象限：

| 象限 | 景氣 | 通膨 | 偏好板塊 |
|------|------|------|----------|
| 復甦期 | ↑ 回升 | ↓ 低 | 景氣循環、消費 |
| 擴張期 | ↑ 高 | ↑ 升 | 科技、原材料 |
| 過熱期 | → 高原 | ↑ 高 | 能源、高股息 |
| 滯脹期 | ↓ 降 | ↑ 高 | 公用事業、防禦型金融 |

**本系統應用：**
- 每季根據 PMI、CPI、GDP 缺口判斷象限
- 象限決定偏好板塊與 WACC 景氣懲罰溢價
- 當前（2026 Q2）：溫和擴張轉過熱 → 偏好金融、電信，WACC +150 bps

**參考：** Merrill Lynch Investment Clock (2004)、Fidelity Sector Rotation Framework
        """)

    with tab2:
        st.markdown("""
### 業主盈餘 DCF 估值

**業主盈餘（Buffett, 1986）：**
```
業主盈餘 = 淨利 + 折舊/攤銷 − 資本支出（維持性）
```

**折現率（WACC）組成：**

| 項目 | 數值 | 說明 |
|------|------|------|
| 無風險利率 | 1.5% | 台灣10年期公債 |
| Beta × ERP | Beta × 5.5% | 系統性風險補償 |
| 地緣政治緩衝 | +1.5% | 台灣海峽風險 |
| 景氣懲罰 | +1.5%（過熱/滯脹） | 景氣不確定性 |

**計算流程：**
1. 業主盈餘每股為基礎現金流
2. 以 yfinance 成長率估計（上限 15%）成長 5 年
3. 以永續成長率 2% 計算終值（Gordon Growth Model）
4. WACC 折現取現值
5. **安全邊際價 = 內在價值 × 80%**

**殖利率計算說明：**
> yfinance 對台股回傳的 `dividendYield` 值格式不一：部分為小數（0.035 = 3.5%），
> 部分已為百分比整數（3.5）。本系統透過判斷原始值是否 > 1 來自動修正，
> 確保顯示數值為正確的百分比格式。

**參考：** Buffett (1986)、Damodaran (2012)、Graham (1949)
        """)

    with tab3:
        st.markdown("""
### 法醫會計評分

**Piotroski F-Score（2000）— 最高 7 分**

| 指標 | 計分條件 |
|------|----------|
| ROE | > 0 |
| ROA | > 0 |
| 營業現金流 | > 0 |
| 現金流品質 | 營業現金流 > 淨利 |
| 負債比 | 負債/權益 < 100% |
| 流動比率 | > 1.0 |
| 盈餘成長 | earningsGrowth > 0 |

≥5 強健 ｜ 3-4 普通 ｜ <3 偏弱

---

**Beneish M-Score 應計代理（1999）**
```
應計比率 = （淨利 − 營業現金流）/ |淨利|
```
> 0.5 → 疑似盈餘虛增

---

**Altman Z-Score 代理（1968）**
```
Z代理 = ROE×2 + 流動比率×0.5 + P/B×0.3
```
< 1.5 危機 ｜ 1.5-3 灰色 ｜ > 3 安全

**參考：** Piotroski (2000)、Beneish (1999)、Altman (1968)
        """)

    with tab4:
        st.markdown("""
### 七步驟選股 SOP

```
步驟一：確認景氣象限
  └─ 主儀表板 → 查看景氣狀態與偏好板塊

步驟二：動態掃描候選標的
  └─ 動態股票掃描 → 在偏好板塊中篩選低本益比/高殖利率個股

步驟三：個股深度估值
  └─ 選股與完整估值 → 執行 DCF，取得內在價值與 MOS 價格

步驟四：法醫財務篩選
  └─ 確認 Piotroski ≥ 3、無 Beneish 警示、Altman Z 非危機區

步驟五：景氣適配確認
  └─ 確認個股板塊符合當前景氣偏好

步驟六：買進條件
  └─ 股價 ≤ MOS 價 + 景氣符合 + Piotroski ≥ 3

步驟七：持倉管理
  └─ 股價 > 內在價值 → 考慮減碼
  └─ 每季更新景氣判斷並重新掃描
```
        """)

st.markdown("---")
st.caption("IMFS v2.5 ｜ 業主盈餘 · 景氣調整 WACC · 法醫會計 · 台灣市場專用 ｜ 參考：Buffett、Damodaran、Graham、Piotroski、Beneish、Altman、ML Investment Clock")
