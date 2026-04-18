# =====================================================
# IMFS v2.6 – 機構級台股輪動儀表板
# 深色石板主題 (Dark Slate Pro) + 完整估值系統
# =====================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np

st.set_page_config(
    page_title="IMFS v2.6 台股儀表板",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 全域樣式：Dark Slate Pro ──────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── 基礎 ── */
html, body, [class*="css"] {
    font-family: 'Inter', 'Noto Sans TC', 'Microsoft JhengHei', sans-serif;
    color: #e2e8f0;
}
.main { background-color: #0f172a; }
.main .block-container {
    padding: 2rem 2.5rem 3rem 2.5rem;
    max-width: 1440px;
    background-color: #0f172a;
}

/* ── 側邊欄 ── */
[data-testid="stSidebar"] {
    background-color: #0b1120 !important;
    border-right: 1px solid #1e2d45;
}
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
[data-testid="stSidebar"] .stRadio label {
    font-size: 0.875rem !important;
    padding: 0.35rem 0 !important;
}
[data-testid="stSidebar"] hr { border-color: #1e2d45 !important; }

/* ── 頁面標題 ── */
.page-header {
    margin-bottom: 0.25rem;
}
.page-title {
    font-size: 1.75rem;
    font-weight: 700;
    color: #f1f5f9;
    letter-spacing: -0.02em;
    margin: 0;
}
.page-subtitle {
    font-size: 0.8rem;
    color: #64748b;
    margin-top: 0.2rem;
    margin-bottom: 1.5rem;
}

/* ── KPI 卡片 ── */
.kpi-card {
    background: #1e293b;
    border: 1px solid #2d3f55;
    border-radius: 10px;
    padding: 1.1rem 1.3rem;
    height: 100%;
    transition: border-color 0.2s;
}
.kpi-card:hover { border-color: #3b82f6; }
.kpi-label {
    font-size: 0.72rem;
    font-weight: 600;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 0.4rem;
}
.kpi-value {
    font-size: 1.45rem;
    font-weight: 700;
    color: #f1f5f9;
    line-height: 1.2;
}
.kpi-sub {
    font-size: 0.75rem;
    color: #94a3b8;
    margin-top: 0.25rem;
}
.kpi-up   { color: #22c55e !important; }
.kpi-down { color: #f87171 !important; }
.kpi-blue { color: #60a5fa !important; }

/* ── 區塊卡片 ── */
.section-card {
    background: #1e293b;
    border: 1px solid #2d3f55;
    border-radius: 10px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1.25rem;
}
.section-title {
    font-size: 0.95rem;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 1rem;
    padding-bottom: 0.6rem;
    border-bottom: 1px solid #2d3f55;
}

/* ── 訊號徽章 ── */
.badge {
    display: inline-block;
    padding: 0.3rem 0.9rem;
    border-radius: 20px;
    font-size: 0.82rem;
    font-weight: 600;
    letter-spacing: 0.03em;
}
.badge-buy   { background: #052e16; color: #4ade80; border: 1px solid #16a34a; }
.badge-hold  { background: #2d1f00; color: #fbbf24; border: 1px solid #d97706; }
.badge-avoid { background: #2d0a0a; color: #f87171; border: 1px solid #dc2626; }

/* ── 分隔線 ── */
.divider {
    border: none;
    border-top: 1px solid #1e2d45;
    margin: 1.5rem 0;
}

/* ── 表格 ── */
[data-testid="stDataFrame"] {
    border: 1px solid #2d3f55 !important;
    border-radius: 8px;
    overflow: hidden;
}
.stDataFrame table { background: #1e293b !important; }
.stDataFrame th { background: #162032 !important; color: #94a3b8 !important; font-size: 0.78rem !important; }
.stDataFrame td { color: #e2e8f0 !important; font-size: 0.83rem !important; }

/* ── 輸入/選擇元件 ── */
[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] select {
    background: #1e293b !important;
    border-color: #2d3f55 !important;
    color: #e2e8f0 !important;
    border-radius: 7px !important;
}
[data-baseweb="select"] { background: #1e293b !important; }

/* ── 按鈕 ── */
.stButton > button[kind="primary"] {
    background: #2563eb;
    border: none;
    color: #fff;
    font-weight: 600;
    border-radius: 8px;
    padding: 0.5rem 1.4rem;
    font-size: 0.875rem;
    transition: background 0.2s;
}
.stButton > button[kind="primary"]:hover { background: #1d4ed8; }
.stButton > button[kind="secondary"] {
    background: transparent;
    border: 1px solid #2d3f55;
    color: #94a3b8;
    border-radius: 8px;
}

/* ── Metric 覆寫 ── */
[data-testid="stMetricValue"]  { font-size: 1.2rem !important; color: #f1f5f9 !important; }
[data-testid="stMetricLabel"]  { font-size: 0.72rem !important; color: #64748b !important; text-transform: uppercase; letter-spacing: 0.06em; }
[data-testid="stMetricDelta"]  { font-size: 0.78rem !important; }

/* ── Info / Warning / Success ── */
[data-testid="stAlert"] { border-radius: 8px; }
div[data-baseweb="notification"] { border-radius: 8px !important; }

/* ── Tab ── */
[data-baseweb="tab-list"] { background: #1e293b; border-radius: 8px; padding: 3px; gap: 2px; }
[data-baseweb="tab"] { border-radius: 6px !important; color: #94a3b8 !important; font-size: 0.83rem !important; }
[aria-selected="true"] { background: #2563eb !important; color: #fff !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #1e293b;
    border: 1px solid #2d3f55 !important;
    border-radius: 8px;
}

/* ── Plotly chart 배경 투명 처리 ── */
.js-plotly-plot { border-radius: 8px; overflow: hidden; }

/* ── 滑桿 ── */
[data-testid="stSlider"] > div > div { color: #94a3b8; }
</style>
""", unsafe_allow_html=True)

# ── Plotly 共用主題 ─────────────────────────────────────────────────────────
PLOT_THEME = dict(
    plot_bgcolor  = "#1e293b",
    paper_bgcolor = "#1e293b",
    font          = dict(color="#cbd5e1", size=12),
    xaxis         = dict(gridcolor="#2d3f55", linecolor="#2d3f55"),
    yaxis         = dict(gridcolor="#2d3f55", linecolor="#2d3f55"),
    margin        = dict(t=40, b=30, l=10, r=10),
)
COLORS_MAIN  = ["#3b82f6","#22c55e","#f59e0b","#f87171","#a78bfa","#34d399"]
COLORS_CHART = ["#1d4ed8","#2563eb","#3b82f6","#93c5fd"]

# ====================== 參數設定 ======================
class IMFS_Config:
    REGIME_PENALTY  = 150
    ERP             = 5.5
    GEO_BUFFER      = 150
    TRANS_COST      = 0.003
    MOS             = 0.20
    RF              = 0.015
    TAX_RATE        = 0.20
    TERMINAL_GROWTH = 0.02

# ====================== 台股標的 ======================
TAIWAN_STOCK_UNIVERSE = {
    '科技類': [
        ('2330','TSMC',   '台灣積體電路製造'),
        ('2317','鴻海',   '鴻海精密工業'),
        ('2454','聯發科', '聯發科技'),
        ('2308','台達電', '台達電子工業'),
        ('2382','廣達',   '廣達電腦'),
        ('3231','緯創',   '緯創資通'),
        ('2353','宏碁',   '宏碁股份有限公司'),
        ('2303','聯電',   '聯華電子'),
        ('2409','友達',   '友達光電'),
        ('3034','聯詠',   '聯詠科技'),
        ('2379','瑞昱',   '瑞昱半導體'),
        ('2344','華邦電', '華邦電子'),
        ('2357','英業達', '英業達股份有限公司'),
        ('2376','技嘉',   '技嘉科技'),
        ('3711','創意',   '創意電子'),
    ],
    '金融類': [
        ('2881','富邦金', '富邦金融控股'),
        ('2882','國泰金', '國泰金融控股'),
        ('2884','玉山金', '玉山金融控股'),
        ('2885','元大金', '元大金融控股'),
        ('2886','兆豐金', '兆豐金融控股'),
        ('2887','台新金', '台新金融控股'),
        ('2888','新光金', '新光金融控股'),
        ('2890','永豐金', '永豐金融控股'),
        ('2891','中信金', '中國信託金融控股'),
        ('2892','第一金', '第一金融控股'),
        ('5876','上海商銀','上海商業儲蓄銀行'),
    ],
    '電信與公用事業': [
        ('2412','中華電', '中華電信'),
        ('4904','遠傳',   '遠傳電信'),
        ('3045','台灣大', '台灣大哥大'),
        ('6505','台塑化', '台灣塑膠化學工業'),
        ('9945','潤泰全', '潤泰全球'),
    ],
    '工業與原材料': [
        ('2002','中鋼',    '中國鋼鐵'),
        ('1301','台塑',    '台灣塑膠工業'),
        ('1303','南亞',    '南亞塑膠工業'),
        ('1326','台化',    '台灣化學纖維'),
        ('2105','正新',    '正新橡膠工業'),
        ('1402','遠東新',  '遠東新世紀'),
        ('2009','東和鋼鐵','東和鋼鐵企業'),
        ('1434','福懋',    '福懋興業'),
    ],
    '消費與零售': [
        ('2912','統一超', '統一超商（7-ELEVEN）'),
        ('1216','統一',   '統一企業'),
        ('2207','和泰車', '和泰汽車'),
        ('2103','亞泥',   '亞洲水泥'),
        ('9910','豐泰',   '豐泰企業'),
        ('6239','力成',   '力成科技'),
    ],
}

TICKER_LOOKUP = {
    t: (s, f, sec)
    for sec, stk in TAIWAN_STOCK_UNIVERSE.items()
    for t, s, f in stk
}

# ====================== 景氣狀態 ======================
current_regime  = "溫和擴張（過熱／滯脹傾向）"
current_bias    = "品質、低波動、自由現金流／股息殖利率"
current_sectors = ["金融類", "電信與公用事業"]

historical_data = {
    '季度':           ['2023 Q1-Q2','2023 Q3-Q4','2024 Q1-Q2','2024 Q3-Q4','2025 Q1-Q2','2025 Q3-Q4','2026 Q1'],
    '景氣狀態':       ['擴張','擴張','擴張','擴張','溫和擴張','溫和擴張','溫和擴張/過熱'],
    'IMFS報酬_%':     [29.0, 26.5, 21.0, 18.5, 21.0, 14.5, 11.0],
    '加權指數報酬_%':  [21.0, 23.5, 17.5, 14.5, 23.5, 13.0, 22.0],
}
df_hist = pd.DataFrame(historical_data)

# ====================== 工具函數 ======================

def _is_overheat() -> bool:
    return any(k in current_regime for k in ("過熱","滯脹"))

def _norm_div(raw) -> float:
    """yfinance dividendYield：>1 視為已是百分比；<=1 乘以100"""
    if raw is None: return 0.0
    v = float(raw)
    return v if v > 1.0 else v * 100.0

def _badge(signal: str) -> str:
    cls = "badge-buy" if "買進" in signal else "badge-hold" if "持有" in signal else "badge-avoid"
    return f'<span class="badge {cls}">{signal}</span>'

def _kpi(label: str, value: str, sub: str = "", color: str = "") -> str:
    val_cls = f"kpi-value {color}" if color else "kpi-value"
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return f"""<div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="{val_cls}">{value}</div>
        {sub_html}
    </div>"""

@st.cache_data(ttl=300)
def fetch_info(ticker: str) -> dict:
    try: return yf.Ticker(ticker + ".TW").info
    except: return {}

@st.cache_data(ttl=300)
def fetch_cashflow(ticker: str) -> pd.DataFrame:
    try: return yf.Ticker(ticker + ".TW").cashflow
    except: return pd.DataFrame()

@st.cache_data(ttl=300)
def download_prices(tickers: tuple, start, end) -> dict:
    data = {}
    for t in tickers:
        try:
            h = yf.download(t+".TW", start=start, end=end, progress=False, auto_adjust=True)
            if h.empty: continue
            c = h["Close"]
            if isinstance(c, pd.DataFrame): c = c.iloc[:,0]
            s = c.squeeze()
            if isinstance(s, pd.Series) and not s.empty:
                data[t] = s
        except: pass
    return data

def _cf_row(cf: pd.DataFrame, *keys) -> float:
    for k in keys:
        if k in cf.index:
            v = cf.loc[k].iloc[0]
            return float(v) if pd.notna(v) else 0.0
    return 0.0

def calc_returns(prices: dict, weights: np.ndarray):
    clean = {k: v.squeeze() for k,v in prices.items() if isinstance(v.squeeze(), pd.Series)}
    if not clean: return None, None
    df = pd.DataFrame(clean).dropna()
    if df.empty: return None, None
    w = weights[:df.shape[1]]; w = w/w.sum()
    ret = df.pct_change().fillna(0)
    pr  = (ret*w).sum(axis=1)
    return (1+pr).cumprod()-1, pr

# ====================== 完整估值函數 ======================

def run_valuation(ticker: str, company: str, sector: str):
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:1rem;margin-bottom:0.5rem;">
        <div style="font-size:1.4rem;font-weight:700;color:#f1f5f9;">{ticker} — {company}</div>
        <div style="font-size:0.78rem;color:#64748b;background:#1e293b;border:1px solid #2d3f55;
                    border-radius:6px;padding:3px 10px;">{sector}</div>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("從 Yahoo Finance 取得資料…"):
        info = fetch_info(ticker)
        cf   = fetch_cashflow(ticker)

    if not info:
        st.error("無法取得資料，請確認股票代號後再試。")
        return

    price  = float(info.get('currentPrice') or info.get('regularMarketPrice') or 0)
    shares = float(info.get('sharesOutstanding') or 1)
    beta   = float(info.get('beta') or 1.0)
    mktcap = float(info.get('marketCap') or price*shares)
    debt   = float(info.get('totalDebt') or 0)

    if not cf.empty:
        ni    = _cf_row(cf,'Net Income','NetIncome')
        da    = _cf_row(cf,'Depreciation And Amortization','Reconciled Depreciation','DepreciationAndAmortization')
        capex = abs(_cf_row(cf,'Capital Expenditure','CapitalExpenditures','Purchase Of Property Plant And Equipment'))
        oe    = ni + da - capex
    else:
        ni=da=capex=0.0; oe=float(info.get('freeCashflow') or 0)
    oe_ps = oe/shares if shares>0 else 0.0

    rf  = IMFS_Config.RF
    geo = IMFS_Config.GEO_BUFFER/10_000
    rp  = IMFS_Config.REGIME_PENALTY/10_000 if _is_overheat() else 0.0
    coe = rf + beta*(IMFS_Config.ERP/100) + geo + rp
    tc  = mktcap+debt; ew=mktcap/tc if tc>0 else 1.0
    ie  = abs(float(info.get('interestExpense') or 0))
    cod = (ie/debt) if debt>0 and ie>0 else 0.03
    wacc = ew*coe + (1-ew)*cod*(1-IMFS_Config.TAX_RATE)

    g5  = max(0.0,min(float(info.get('earningsGrowth') or info.get('revenueGrowth') or 0.05),0.15))
    tg  = IMFS_Config.TERMINAL_GROWTH
    pv5 = sum(oe_ps*(1+g5)**y/(1+wacc)**y for y in range(1,6))
    tv  = (oe_ps*(1+g5)**5*(1+tg)/(wacc-tg)) if wacc>tg else 0.0
    tvp = tv/(1+wacc)**5
    iv  = pv5+tvp; mos=iv*(1-IMFS_Config.MOS)
    upside=((iv-price)/price*100) if price>0 else 0.0

    signal = ("買進 — 低於安全邊際價" if price>0 and price<=mos else
              "持有 — 低於內在價值"   if price>0 and price<=iv  else
              "觀望 — 高於內在價值")

    roe=float(info.get('returnOnEquity') or 0)
    roa=float(info.get('returnOnAssets') or 0)
    de =float(info.get('debtToEquity') or 0)
    cr =float(info.get('currentRatio') or 0)
    ocf=float(info.get('operatingCashflow') or 0)
    ni_i=float(info.get('netIncomeToCommon') or 0)
    pb =float(info.get('priceToBook') or 0)
    dy =_norm_div(info.get('dividendYield'))

    pf = sum([roe>0,roa>0,ocf>0,ocf>ni_i,de<100,cr>1.0,float(info.get('earningsGrowth') or 0)>0])
    pf_lbl = "強健" if pf>=5 else "普通" if pf>=3 else "偏弱"
    ben = "⚠️ 疑似盈餘虛增" if (ni_i-ocf)/max(abs(ni_i),1)>0.5 else "✅ 正常"
    z   = roe*2+cr*0.5+pb*0.3
    z_lbl = "⚠️ 危機" if z<1.5 else "🟡 灰色" if z<3 else "✅ 安全"

    # ── 訊號 + 頂部 KPI ──────────────────────────────────────────
    st.markdown(_badge(signal), unsafe_allow_html=True)
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    with c1: st.markdown(_kpi("目前股價",       f"NT${price:,.1f}"   if price else "—"), unsafe_allow_html=True)
    with c2: st.markdown(_kpi("內在價值（DCF）", f"NT${iv:,.1f}"      if iv    else "—","", "kpi-blue"), unsafe_allow_html=True)
    with c3: st.markdown(_kpi("安全邊際價",      f"NT${mos:,.1f}"     if mos   else "—", "-20%"), unsafe_allow_html=True)
    with c4:
        up_color = "kpi-up" if upside > 0 else "kpi-down"
        st.markdown(_kpi("距內在價值", f"{upside:+.1f}%"  if price else "—","", up_color), unsafe_allow_html=True)
    with c5: st.markdown(_kpi("WACC", f"{wacc*100:.2f}%"), unsafe_allow_html=True)
    with c6: st.markdown(_kpi("股息殖利率", f"{dy:.2f}%"), unsafe_allow_html=True)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # ── WACC & DCF 圖表 ───────────────────────────────────────────
    left, right = st.columns(2)
    with left:
        st.markdown('<div class="section-title">WACC 拆解</div>', unsafe_allow_html=True)
        wdf = pd.DataFrame({
            "組成": ["無風險利率","Beta×ERP","地緣緩衝","景氣懲罰","→股權成本","WACC"],
            "值%":  [rf*100, beta*IMFS_Config.ERP, IMFS_Config.GEO_BUFFER/100,
                     IMFS_Config.REGIME_PENALTY/100 if _is_overheat() else 0,
                     coe*100, wacc*100],
        })
        fig_w = px.bar(wdf, x="組成", y="值%", text_auto=".2f",
                       color_discrete_sequence=["#3b82f6"])
        fig_w.update_traces(textfont_color="#f1f5f9", textposition="outside")
        fig_w.update_layout(**PLOT_THEME, height=280, showlegend=False,
                             title=dict(text="",font_size=0))
        st.plotly_chart(fig_w, use_container_width=True)

    with right:
        st.markdown('<div class="section-title">DCF 估值拆解</div>', unsafe_allow_html=True)
        ddf = pd.DataFrame({
            "項目": ["5年現金流現值","永續價值現值","內在價值","安全邊際價"],
            "NT$":  [pv5, tvp, iv, mos],
        })
        fig_d = px.bar(ddf, x="項目", y="NT$", text_auto=".1f",
                       color="項目", color_discrete_sequence=COLORS_CHART)
        if price:
            fig_d.add_hline(y=price, line_dash="dot", line_color="#f87171",
                            annotation_text=f"現價 {price:.0f}",
                            annotation_font_color="#f87171",
                            annotation_bgcolor="#2d0a0a")
        fig_d.update_traces(textfont_color="#f1f5f9")
        fig_d.update_layout(**PLOT_THEME, height=280, showlegend=False)
        st.plotly_chart(fig_d, use_container_width=True)

    # ── 業主盈餘 ─────────────────────────────────────────────────
    st.markdown('<div class="section-title">業主盈餘（Owner Earnings）</div>', unsafe_allow_html=True)
    oe1,oe2,oe3,oe4 = st.columns(4)
    if not cf.empty:
        with oe1: st.markdown(_kpi("淨利",       f"NT${ni/1e9:.2f}B"), unsafe_allow_html=True)
        with oe2: st.markdown(_kpi("＋折舊攤銷", f"NT${da/1e9:.2f}B"), unsafe_allow_html=True)
        with oe3: st.markdown(_kpi("－資本支出", f"NT${capex/1e9:.2f}B"), unsafe_allow_html=True)
        with oe4: st.markdown(_kpi("＝業主盈餘", f"NT${oe/1e9:.2f}B","","kpi-blue"), unsafe_allow_html=True)
    else:
        with oe1: st.markdown(_kpi("自由現金流（替代）", f"NT${oe/1e9:.2f}B"), unsafe_allow_html=True)
        st.caption("現金流量表資料不足，以自由現金流替代")

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # ── 法醫評分 ─────────────────────────────────────────────────
    st.markdown('<div class="section-title">財務健全度（法醫會計）</div>', unsafe_allow_html=True)
    fa1,fa2,fa3 = st.columns(3)
    with fa1: st.markdown(_kpi("Piotroski F-Score", f"{pf}/7",  pf_lbl), unsafe_allow_html=True)
    with fa2: st.markdown(_kpi("Beneish 應計項目",  ben), unsafe_allow_html=True)
    with fa3: st.markdown(_kpi("Altman Z（代理）",  z_lbl, f"Z = {z:.2f}"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    fin_df = pd.DataFrame({
        "指標": ["ROE","ROA","負債／權益","流動比率","P/B","股息殖利率"],
        "數值": [f"{roe*100:.1f}%" if roe else "—",
                 f"{roa*100:.1f}%" if roa else "—",
                 f"{de:.1f}%"      if de   else "—",
                 f"{cr:.2f}"       if cr   else "—",
                 f"{pb:.2f}"       if pb   else "—",
                 f"{dy:.2f}%"],
        "說明": ["股東權益報酬率","資產報酬率","財務槓桿","短期流動能力","股價淨值比","年化股息殖利率"],
    })
    st.dataframe(fin_df, use_container_width=True, hide_index=True,
                 column_config={
                     "指標": st.column_config.TextColumn(width=140),
                     "數值": st.column_config.TextColumn(width=110),
                     "說明": st.column_config.TextColumn(width=200),
                 })

    # ── 加入觀察清單 ─────────────────────────────────────────────
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    col_a, col_b = st.columns([1,4])
    with col_a:
        if st.button("➕ 加入觀察清單", type="secondary"):
            wl = st.session_state.get("watchlist", [])
            entry = {"代號":ticker,"公司":company,"板塊":sector,"股價":price,
                     "內在價值":round(iv,1),"MOS價":round(mos,1),
                     "訊號":signal,"Piotroski":f"{pf}/7","殖利率%":f"{dy:.2f}%"}
            if ticker not in [w["代號"] for w in wl]:
                wl.append(entry); st.session_state["watchlist"]=wl
                st.success(f"✅ {ticker} 已加入觀察清單")
            else:
                st.info(f"{ticker} 已在清單中")


# ====================== 掃描器 ======================
class MarketScanner:
    def __init__(self, sectors): self.sectors = sectors

    @st.cache_data(ttl=600)
    def _scan(_self, st, pe, pb_t, dy):
        rows=[]
        for sec in st:
            for tkr,_,full in TAIWAN_STOCK_UNIVERSE.get(sec,[]):
                try:
                    i   = yf.Ticker(tkr+".TW").info
                    _pe = float(i.get('trailingPE') or float('inf'))
                    _pb = float(i.get('priceToBook') or float('inf'))
                    _dy = _norm_div(i.get('dividendYield'))
                    sc  = int(_pe<pe)+int(_pb<pb_t)+int(_dy>dy)
                    if sc>=1:
                        rows.append({
                            '代號':tkr,'公司名稱':full,'板塊':sec,
                            '股價':round(float(i.get('currentPrice') or 0),2),
                            'P/E':round(_pe,2) if _pe!=float('inf') else None,
                            'P/B':round(_pb,2) if _pb!=float('inf') else None,
                            '殖利率%':round(_dy,2),
                            '市值(十億)':round(float(i.get('marketCap') or 0)/1e9,1) or None,
                            '評分':sc,
                        })
                except: pass
        rows.sort(key=lambda x:x['評分'],reverse=True)
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    def scan(self,pe=15,pb=1.2,dy=2.0):
        return self._scan(tuple(self.sectors),pe,pb,dy)


# ====================== 側邊欄 ======================
with st.sidebar:
    st.markdown("""
    <div style="padding:1rem 0.5rem 0.5rem;">
        <div style="font-size:1rem;font-weight:700;color:#f1f5f9;">IMFS v2.6</div>
        <div style="font-size:0.72rem;color:#64748b;margin-top:2px;">台股機構級輪動系統</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    page = st.radio("", [
        "📊  主儀表板",
        "🏷️  選股與完整估值",
        "🔍  快速查詢",
        "🎯  動態股票掃描",
        "📈  投資組合模擬",
        "📋  觀察清單",
        "📖  方法論說明",
    ], label_visibility="collapsed")

    st.markdown("---")
    st.markdown(f"""
    <div style="font-size:0.72rem;color:#64748b;line-height:1.8;">
        <div style="color:#94a3b8;font-weight:600;margin-bottom:4px;">當前景氣</div>
        <div style="color:#fbbf24;">{current_regime}</div>
        <div style="color:#94a3b8;font-weight:600;margin-top:8px;margin-bottom:4px;">偏好板塊</div>
        {"".join(f'<div style="color:#60a5fa;">▸ {s}</div>' for s in current_sectors)}
    </div>
    """, unsafe_allow_html=True)

# ====================== 頁面路由 ======================

# ── 主儀表板 ─────────────────────────────────────────────────────────────────
if page == "📊  主儀表板":
    st.markdown('<div class="page-title">主儀表板</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">景氣輪動狀態 ｜ 即時行動建議 ｜ 歷史績效</div>', unsafe_allow_html=True)

    k1,k2,k3,k4 = st.columns(4)
    with k1: st.markdown(_kpi("景氣狀態",     current_regime,"2026 Q2","kpi-blue"), unsafe_allow_html=True)
    with k2: st.markdown(_kpi("偏好板塊",     "、".join(current_sectors)), unsafe_allow_html=True)
    with k3: st.markdown(_kpi("台灣 PMI（3月）","53.3","↓ -2.1 MoM","kpi-down"), unsafe_allow_html=True)
    with k4: st.markdown(_kpi("WACC 景氣加罰", "+150 bps","過熱期生效","kpi-down"), unsafe_allow_html=True)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    left, right = st.columns([3,2])
    with left:
        st.markdown('<div class="section-title">立即行動建議（2026 Q2）</div>', unsafe_allow_html=True)
        st.info("""
**資產配置：** 60–80% 布局品質／自由現金流／高股息
**偏好板塊：** 金融類、電信與公用事業
**買進門檻：** 股價 ≤ 安全邊際價（內在價值 × 80%）
**WACC：** 本季已加入 +150 bps 景氣懲罰溢價
        """)
    with right:
        st.markdown('<div class="section-title">風險矩陣</div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame({
            "風險":["景氣轉折","地緣政治","通膨急升","流動性"],
            "機率":["中等","高","中高","中等"],
            "對應":["PMI 季檢","WACC +1.5%","WACC +1.5% 懲罰","聚焦大型股"],
        }), use_container_width=True, hide_index=True)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">歷史季度績效（示意數據）</div>', unsafe_allow_html=True)

    t1, t2 = st.tabs(["📊 圖表", "📋 數據表"])
    with t1:
        fig = go.Figure()
        fig.add_bar(x=df_hist['季度'], y=df_hist['IMFS報酬_%'],
                    name="IMFS", marker_color="#3b82f6")
        fig.add_bar(x=df_hist['季度'], y=df_hist['加權指數報酬_%'],
                    name="加權指數", marker_color="#475569")
        fig.update_layout(**PLOT_THEME, barmode='group', height=320,
                          legend=dict(orientation="h",y=1.1),
                          title=dict(text="季度報酬率對比（%）",font=dict(size=13,color="#94a3b8")))
        st.plotly_chart(fig, use_container_width=True)
    with t2:
        st.dataframe(df_hist, use_container_width=True, hide_index=True)

# ── 選股與完整估值 ────────────────────────────────────────────────────────────
elif page == "🏷️  選股與完整估值":
    st.markdown('<div class="page-title">選股與完整估值</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">搜尋台股代號或名稱，執行業主盈餘 DCF 完整估值</div>', unsafe_allow_html=True)

    all_stocks = [{"t":t,"s":s,"f":f,"sec":sec,"disp":f"{t} — {f}  [{sec}]"}
                  for sec,stk in TAIWAN_STOCK_UNIVERSE.items() for t,s,f in stk]

    search = st.text_input("🔍", "", placeholder="輸入代號或名稱（例：2330、台積電、金融）",
                           label_visibility="collapsed")
    q = search.strip().lower()
    filtered = ([x for x in all_stocks if q in x["t"] or q in x["f"].lower()
                 or q in x["s"].lower() or q in x["sec"].lower()]
                if q else all_stocks)

    if not filtered:
        st.warning("查無符合結果。")
    else:
        col_sel, col_btn = st.columns([4,1])
        with col_sel:
            chosen_disp = st.selectbox(f"共 {len(filtered)} 筆結果",
                                       [x["disp"] for x in filtered],
                                       label_visibility="collapsed")
        chosen = next(x for x in filtered if x["disp"]==chosen_disp)

        with col_btn:
            run = st.button("執行估值 ▶", type="primary", use_container_width=True)

        ca,cb,cc = st.columns(3)
        ca.caption(f"代號：`{chosen['t']}.TW`")
        cb.caption(f"板塊：{chosen['sec']}")
        cc.caption(f"景氣適配：{'✅ 符合' if chosen['sec'] in current_sectors else '⚠️ 不符合'}")

        if run:
            st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
            run_valuation(chosen["t"], chosen["f"], chosen["sec"])

# ── 快速查詢 ──────────────────────────────────────────────────────────────────
elif page == "🔍  快速查詢":
    st.markdown('<div class="page-title">快速查詢</div>', unsafe_allow_html=True)
    col1,col2 = st.columns([3,1])
    with col1: tkr = st.text_input("上市／上櫃代號","2881",label_visibility="collapsed")
    with col2:
        st.markdown("<br>",unsafe_allow_html=True)
        fetch_btn = st.button("查詢",type="primary",use_container_width=True)
    if fetch_btn:
        info = fetch_info(tkr)
        if info:
            dy = _norm_div(info.get('dividendYield'))
            r1,r2,r3,r4,r5 = st.columns(5)
            _,full,_ = TICKER_LOOKUP.get(tkr,("","",""))
            with r1: st.markdown(_kpi("公司名稱", info.get('longName',full) or full), unsafe_allow_html=True)
            with r2: st.markdown(_kpi("股價", f"NT${info.get('currentPrice','—')}"), unsafe_allow_html=True)
            with r3: st.markdown(_kpi("P/E", f"{info.get('trailingPE','—')}"), unsafe_allow_html=True)
            with r4: st.markdown(_kpi("P/B", f"{info.get('priceToBook','—')}"), unsafe_allow_html=True)
            with r5: st.markdown(_kpi("殖利率", f"{dy:.2f}%"), unsafe_allow_html=True)
        else:
            st.error("無法取得資料，請確認代號。")

# ── 動態掃描 ──────────────────────────────────────────────────────────────────
elif page == "🎯  動態股票掃描":
    st.markdown('<div class="page-title">動態市場掃描</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">景氣感知篩選 ｜ 依偏好板塊自動調整門檻</div>', unsafe_allow_html=True)

    with st.expander("⚙️ 掃描參數", expanded=True):
        c1,c2,c3,c4 = st.columns(4)
        sel = c1.multiselect("板塊",list(TAIWAN_STOCK_UNIVERSE.keys()),default=current_sectors)
        pe  = c2.number_input("P/E 上限", value=12 if "品質" in current_bias else 18, min_value=1, max_value=50)
        pb  = c3.number_input("P/B 上限", value=1.0 if "品質" in current_bias else 1.5, min_value=0.1, max_value=10.0, step=0.1)
        dy  = c4.number_input("殖利率下限 %", value=3.0 if "品質" in current_bias else 2.0, min_value=0.0, max_value=15.0, step=0.5)

    if sel and st.button("立即掃描 ▶", type="primary", use_container_width=True):
        with st.spinner("掃描中…"):
            res = MarketScanner(sel).scan(pe, pb, dy)

        if not res.empty:
            st.success(f"找到 **{len(res)}** 檔候選標的")
            ch1,ch2 = st.columns(2)
            with ch1:
                fig_p = px.pie(res, names='板塊', title="板塊分布",
                               color_discrete_sequence=COLORS_MAIN)
                fig_p.update_layout(**PLOT_THEME, height=260)
                st.plotly_chart(fig_p, use_container_width=True)
            with ch2:
                sc = res['評分'].value_counts().reset_index()
                sc.columns=['評分','數量']
                fig_sc = px.bar(sc,x='評分',y='數量',title="評分分布",
                                color='數量',color_continuous_scale='Blues')
                fig_sc.update_layout(**PLOT_THEME,height=260,showlegend=False)
                st.plotly_chart(fig_sc,use_container_width=True)

            st.dataframe(res, use_container_width=True, hide_index=True,
                column_config={
                    "代號":      st.column_config.TextColumn(width=70),
                    "公司名稱":  st.column_config.TextColumn(width=160),
                    "板塊":      st.column_config.TextColumn(width=130),
                    "股價":      st.column_config.NumberColumn("股價(NT$)", format="%.2f"),
                    "P/E":       st.column_config.NumberColumn(format="%.2f"),
                    "P/B":       st.column_config.NumberColumn(format="%.2f"),
                    "殖利率%":   st.column_config.NumberColumn("殖利率%", format="%.2f"),
                    "市值(十億)":st.column_config.NumberColumn("市值(十億)", format="%.1f"),
                    "評分":      st.column_config.ProgressColumn("評分", min_value=0, max_value=3),
                })
        else:
            st.warning("目前條件下無符合標的，請調整篩選參數。")

# ── 投資組合模擬 ───────────────────────────────────────────────────────────────
elif page == "📈  投資組合模擬":
    st.markdown('<div class="page-title">投資組合回測模擬器</div>', unsafe_allow_html=True)

    with st.expander("⚙️ 策略設定", expanded=True):
        c1,c2 = st.columns(2)
        yrs   = c1.slider("回測期間（年）",1,5,3)
        strat = c2.selectbox("策略",[
            "成長型（2330、2308、3231）",
            "品質／高股息（2881、2412、2882）",
            "均衡配置（2330、2881、2308）",
        ])

    smap = {
        "成長型（2330、2308、3231）":       (["2330","2308","3231"],np.array([.40,.35,.25]),"成長型"),
        "品質／高股息（2881、2412、2882）":  (["2881","2412","2882"],np.array([.40,.35,.25]),"品質／高股息"),
        "均衡配置（2330、2881、2308）":      (["2330","2881","2308"],np.array([.33,.33,.34]),"均衡配置"),
    }
    tkrs,wts,name = smap[strat]
    end_dt = datetime.now(); start_dt = end_dt-timedelta(days=365*yrs)
    st.info(f"回測 **{name}** ｜ {start_dt.date()} → {end_dt.date()}")

    with st.spinner("下載歷史價格…"):
        prices = download_prices(tuple(tkrs),start_dt,end_dt)

    cum,dret = calc_returns(prices,wts)
    if cum is not None and len(cum)>0:
        tr  = cum.iloc[-1]*100
        ar  = ((1+cum.iloc[-1])**(1/yrs)-1)*100
        vol = dret.std()*np.sqrt(252)*100
        shr = (ar-2.0)/vol if vol>0 else 0
        mdd = (cum.cummax()-cum).max()*100

        m1,m2,m3,m4,m5 = st.columns(5)
        with m1: st.markdown(_kpi("總報酬",    f"{tr:.1f}%","",  "kpi-up" if tr>0 else "kpi-down"), unsafe_allow_html=True)
        with m2: st.markdown(_kpi("年化報酬",  f"{ar:.1f}%","",  "kpi-up" if ar>0 else "kpi-down"), unsafe_allow_html=True)
        with m3: st.markdown(_kpi("年化波動率",f"{vol:.1f}%"), unsafe_allow_html=True)
        with m4: st.markdown(_kpi("夏普比率",  f"{shr:.2f}","",  "kpi-blue"), unsafe_allow_html=True)
        with m5: st.markdown(_kpi("最大回撤",  f"-{mdd:.1f}%","","kpi-down"), unsafe_allow_html=True)

        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=cum.index, y=cum.values*100,
                                   mode='lines', name=name,
                                   fill='tozeroy', line=dict(color='#3b82f6',width=2),
                                   fillcolor='rgba(59,130,246,0.1)'))
        fig3.add_hline(y=0, line_dash="dash", line_color="#475569", line_width=1)
        fig3.update_layout(**PLOT_THEME, height=380,
                           title=dict(text=f"{name} — 累積報酬率（%）",
                                      font=dict(size=13,color="#94a3b8")),
                           xaxis_title="日期", yaxis_title="累積報酬 (%)")
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.warning("無法計算，部分標的資料不足。請確認網路連線或更換策略。")

# ── 觀察清單 ──────────────────────────────────────────────────────────────────
elif page == "📋  觀察清單":
    st.markdown('<div class="page-title">觀察清單</div>', unsafe_allow_html=True)
    wl = st.session_state.get("watchlist",[])
    if wl:
        st.dataframe(pd.DataFrame(wl), use_container_width=True, hide_index=True)
        if st.button("清空清單", type="secondary"):
            st.session_state["watchlist"]=[]; st.rerun()
    else:
        st.info("清單為空。請至「選股與完整估值」執行估值後加入。")

# ── 方法論說明 ────────────────────────────────────────────────────────────────
elif page == "📖  方法論說明":
    st.markdown('<div class="page-title">方法論說明</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">IMFS v2.6 整合框架：景氣輪動 × 業主盈餘 DCF × 法醫會計</div>', unsafe_allow_html=True)

    t1,t2,t3,t4 = st.tabs(["一、景氣輪動","二、業主盈餘 DCF","三、法醫會計","四、使用流程"])

    with t1:
        st.markdown("""
### Investment Clock 景氣輪動（Merrill Lynch, 2004）
| 象限 | 景氣 | 通膨 | 偏好板塊 |
|------|------|------|----------|
| 復甦期 | ↑ 回升 | ↓ 低 | 景氣循環、消費 |
| 擴張期 | ↑ 高 | ↑ 升 | 科技、原材料 |
| 過熱期 | → 高原 | ↑ 高 | 能源、高股息 |
| 滯脹期 | ↓ 降 | ↑ 高 | 公用事業、防禦型金融 |

**台灣應用：** 每季根據 PMI、CPI 判斷象限 → 決定偏好板塊 + WACC 加罰幅度
        """)
    with t2:
        st.markdown("""
### 業主盈餘 DCF（Buffett, 1986）
```
業主盈餘 = 淨利 + 折舊攤銷 − 資本支出
```
| WACC 組成 | 數值 |
|-----------|------|
| 無風險利率 | 1.5%（台灣10年期公債）|
| Beta × ERP | Beta × 5.5% |
| 地緣政治緩衝 | +1.5%（台海風險）|
| 景氣懲罰 | +1.5%（過熱／滯脹時）|

**安全邊際價 = 內在價值 × 80%**（Margin of Safety）

**殖利率修正：** yfinance 部分台股回傳已是百分比格式（如 3.5 而非 0.035），系統自動判斷修正，確保顯示正確。
        """)
    with t3:
        st.markdown("""
### 法醫會計三大工具
**Piotroski F-Score（2000）— 7分制**
ROE>0、ROA>0、現金流>0、現金流品質、負債比<100%、流動比率>1、盈餘成長

**Beneish M-Score 代理（1999）**
`應計比率 = (淨利−營業現金流)/|淨利|` → >0.5 疑似盈餘虛增

**Altman Z-Score 代理（1968）**
`Z = ROE×2 + 流動比率×0.5 + P/B×0.3`
<1.5 危機 ｜ 1.5-3 灰色 ｜ >3 安全
        """)
    with t4:
        st.markdown("""
### 七步驟選股 SOP
```
1. 景氣確認   → 主儀表板：查看景氣狀態與偏好板塊
2. 掃描候選   → 動態股票掃描：篩選低估值高殖利率個股
3. 深度估值   → 選股與完整估值：DCF 取得內在價值與 MOS 價
4. 法醫篩選   → Piotroski ≥ 3 + 無 Beneish 警示 + Z 非危機
5. 景氣適配   → 板塊符合當前偏好
6. 買進條件   → 股價 ≤ MOS 價 + 景氣符合 + 財務健全
7. 持倉管理   → 股價 > 內在價值 考慮減碼；每季重新評估
```
        """)

# ── 頁腳 ──────────────────────────────────────────────────────────────────────
st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
st.markdown("""
<div style="font-size:0.72rem;color:#334155;text-align:center;">
IMFS v2.6 ｜ 業主盈餘 · 景氣調整 WACC · 法醫會計 · 台灣市場專用<br>
參考文獻：Buffett (1986) · Damodaran (2012) · Graham (1949) · Piotroski (2000) · Beneish (1999) · Altman (1968) · Merrill Lynch Investment Clock (2004)
</div>
""", unsafe_allow_html=True)
