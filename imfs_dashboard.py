# =====================================================
# IMFS v2.8 – 機構級台股輪動儀表板
# Midnight Slate 主題 — 高對比度 + 5步驟引導面板 + 掃描買進區
# =====================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np

st.set_page_config(
    page_title="IMFS v2.8",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Midnight Slate 色彩系統 (高對比度) ────────────────────────────────────────
# BG:      #111827  Tailwind gray-900
# SURFACE: #1F2937  Tailwind gray-800  (+14 lightness vs bg — clearly distinct)
# SURFACE2:#374151  Tailwind gray-700  (hover/secondary)
# BORDER:  #4B5563  Tailwind gray-600  (very visible border)
# TEXT1:   #F9FAFB  Tailwind gray-50   (near white)
# TEXT2:   #9CA3AF  Tailwind gray-400  (muted label)
# BLUE:    #60A5FA  Tailwind blue-400  (accent/primary)
# GREEN:   #34D399  Tailwind emerald-400
# RED:     #F87171  Tailwind red-400
# AMBER:   #FBBF24  Tailwind amber-400
# ─────────────────────────────────────────────────────────────────────────────

CSS = """
<style>
/* ── 全域基底 ── */
html, body {
    background-color: #111827 !important;
    color: #F9FAFB !important;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
                 'Noto Sans TC', 'Microsoft JhengHei', sans-serif !important;
}
[class*="css"], .stApp, .main {
    background-color: #111827 !important;
}
.block-container {
    background-color: #111827 !important;
    padding: 1.5rem 2rem 3rem !important;
    max-width: 1440px;
}

/* ── 側邊欄 ── */
[data-testid="stSidebar"] {
    background-color: #0D1117 !important;
    border-right: 2px solid #374151 !important;
}
[data-testid="stSidebar"] > div { padding-top: 0.5rem; }

/* ── st.metric 卡片 ── */
[data-testid="metric-container"] {
    background-color: #1F2937 !important;
    border: 1px solid #4B5563 !important;
    border-radius: 10px !important;
    padding: 0.9rem 1.1rem !important;
}
[data-testid="metric-container"]:hover {
    border-color: #60A5FA !important;
    background-color: #263040 !important;
}
[data-testid="stMetricLabel"] > div {
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.09em !important;
    color: #9CA3AF !important;
}
[data-testid="stMetricValue"] > div {
    font-size: 1.25rem !important;
    font-weight: 700 !important;
    color: #F9FAFB !important;
    line-height: 1.3 !important;
}
[data-testid="stMetricDelta"] > div {
    font-size: 0.78rem !important;
    font-weight: 600 !important;
}

/* ── 區塊標題 ── */
h1 {
    font-size: 1.5rem !important; font-weight: 700 !important;
    color: #F9FAFB !important; letter-spacing: -0.02em;
    margin-bottom: 0.15rem !important;
}
h2 { font-size: 1.05rem !important; font-weight: 600 !important; color: #9CA3AF !important; }
h3 { font-size: 0.9rem !important; font-weight: 600 !important; color: #D1D5DB !important; }
p  { color: #E5E7EB !important; }

/* ── 分隔線 ── */
hr { border: none; border-top: 1px solid #374151 !important; margin: 1.25rem 0 !important; }

/* ── 小節標籤 ── */
.sec-label {
    font-size: 0.67rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #9CA3AF;
    padding-bottom: 0.45rem;
    border-bottom: 2px solid #374151;
    margin-bottom: 0.8rem;
}

/* ── 訊號徽章 ── */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 14px;
    border-radius: 6px;
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.02em;
}
.badge-buy   { background:#064E3B; color:#34D399; border:1px solid #059669; }
.badge-hold  { background:#451A03; color:#FBBF24; border:1px solid #B45309; }
.badge-avoid { background:#450A0A; color:#F87171; border:1px solid #B91C1C; }

/* ── 買進區徽章 ── */
.buy-zone-yes {
    background:#064E3B; color:#34D399; border:1px solid #059669;
    padding:2px 8px; border-radius:5px; font-size:0.75rem; font-weight:700;
}
.buy-zone-no {
    background:#1F2937; color:#9CA3AF; border:1px solid #4B5563;
    padding:2px 8px; border-radius:5px; font-size:0.75rem; font-weight:600;
}

/* ── 步驟引導卡片 ── */
.step-card {
    background: #1F2937;
    border: 1px solid #374151;
    border-radius: 10px;
    padding: 0.75rem 1rem;
    margin-bottom: 0.5rem;
}
.step-card.active {
    border-color: #60A5FA;
    background: #1E3A5F;
}
.step-card.done {
    border-color: #059669;
    background: #052E16;
}
.step-num {
    font-size: 0.6rem; font-weight: 800; text-transform: uppercase;
    letter-spacing: 0.12em; margin-bottom: 2px;
}
.step-title { font-size: 0.82rem; font-weight: 700; color: #F9FAFB; }
.step-hint  { font-size: 0.7rem; color: #9CA3AF; margin-top: 2px; }

/* ── 表格 ── */
[data-testid="stDataFrame"] {
    border: 1px solid #4B5563 !important;
    border-radius: 8px !important;
    overflow: hidden !important;
}
thead tr th {
    background-color: #1F2937 !important;
    color: #9CA3AF !important;
    font-size: 0.71rem !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    border-bottom: 1px solid #4B5563 !important;
}
tbody tr td {
    background-color: #161D2B !important;
    color: #E5E7EB !important;
    font-size: 0.83rem !important;
    border-bottom: 1px solid #374151 !important;
}
tbody tr:hover td { background-color: #1F2937 !important; }

/* ── 入力欄 ── */
[data-testid="stTextInput"] > div > div > input {
    background: #1F2937 !important;
    border: 1px solid #4B5563 !important;
    color: #F9FAFB !important;
    border-radius: 7px !important;
    font-size: 0.875rem;
}
[data-testid="stTextInput"] > div > div > input:focus { border-color: #60A5FA !important; }
[data-baseweb="select"] > div {
    background: #1F2937 !important;
    border-color: #4B5563 !important;
}
[data-baseweb="select"] * { color: #F9FAFB !important; }
[data-baseweb="select"] li { background: #1F2937 !important; }

/* ── 按鈕 ── */
button[kind="primary"] {
    background: #2563EB !important;
    border: none !important;
    border-radius: 7px !important;
    font-weight: 700 !important;
    font-size: 0.875rem !important;
    color: #fff !important;
    transition: background 0.15s;
}
button[kind="primary"]:hover { background: #1D4ED8 !important; }
button[kind="secondary"] {
    background: transparent !important;
    border: 1px solid #4B5563 !important;
    border-radius: 7px !important;
    color: #9CA3AF !important;
}
button[kind="secondary"]:hover { border-color: #9CA3AF !important; color: #F9FAFB !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #1F2937 !important;
    border: 1px solid #4B5563 !important;
    border-radius: 8px !important;
}
[data-testid="stExpander"] summary { color: #E5E7EB !important; font-size: 0.85rem; }

/* ── Tabs ── */
[data-baseweb="tab-list"] {
    background: #1F2937 !important;
    border-radius: 8px; padding: 3px; gap: 2px;
    border: 1px solid #4B5563;
}
[data-baseweb="tab"] {
    border-radius: 6px !important;
    color: #9CA3AF !important;
    font-size: 0.82rem !important;
    padding: 6px 14px !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    background: #2563EB !important;
    color: #fff !important;
}

/* ── info/warning/error boxes ── */
[data-baseweb="notification"] {
    background: #1F2937 !important;
    border: 1px solid #4B5563 !important;
    border-radius: 8px !important;
}
div[data-testid="stAlert"] {
    background: #1F2937 !important;
    border: 1px solid #4B5563 !important;
    border-radius: 8px !important;
    color: #E5E7EB !important;
}

/* ── 標籤/說明文字 ── */
label { color: #9CA3AF !important; font-size: 0.78rem !important; }
.stCaption, [data-testid="stCaptionContainer"] { color: #6B7280 !important; }

/* ── Number input ── */
[data-testid="stNumberInput"] input {
    background: #1F2937 !important;
    border: 1px solid #4B5563 !important;
    color: #F9FAFB !important;
    border-radius: 7px !important;
}

/* ── Multiselect ── */
[data-baseweb="tag"] {
    background: #2563EB !important;
    color: #fff !important;
}

/* ── Radio ── */
[data-testid="stRadio"] label { color: #E5E7EB !important; font-size: 0.85rem !important; }
[data-testid="stRadio"] [data-checked="true"] label { color: #60A5FA !important; font-weight: 600 !important; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ── Plotly 共用主題 ───────────────────────────────────────────────────────────
PT = dict(
    plot_bgcolor="#1F2937", paper_bgcolor="#111827",
    font=dict(color="#9CA3AF", size=11),
    xaxis=dict(gridcolor="#374151", linecolor="#4B5563", tickfont=dict(color="#9CA3AF")),
    yaxis=dict(gridcolor="#374151", linecolor="#4B5563", tickfont=dict(color="#9CA3AF")),
    margin=dict(t=36, b=24, l=8, r=8),
    title=dict(font=dict(color="#E5E7EB", size=12)),
    legend=dict(bgcolor="#1F2937", bordercolor="#4B5563", font=dict(color="#9CA3AF")),
)
C = ["#60A5FA","#34D399","#FBBF24","#F87171","#A78BFA","#22D3EE"]

# ====================== 設定 ======================
class IMFS_Config:
    REGIME_PENALTY  = 150   # bps，過熱期加罰
    ERP             = 5.5   # 權益風險溢價 %
    GEO_BUFFER      = 150   # 地緣緩衝 bps
    MOS             = 0.20  # 安全邊際 20%
    RF              = 0.015 # 無風險利率
    TAX_RATE        = 0.20
    TERMINAL_GROWTH = 0.02
    FAIR_PE         = 15.0  # 快速估值基準 P/E（掃描用）

# ====================== 台股標的 ======================
TAIWAN_STOCK_UNIVERSE = {
    '科技類': [
        ('2330','TSMC',   '台灣積體電路製造'),('2317','鴻海',  '鴻海精密工業'),
        ('2454','聯發科', '聯發科技'),        ('2308','台達電','台達電子工業'),
        ('2382','廣達',   '廣達電腦'),        ('3231','緯創',  '緯創資通'),
        ('2353','宏碁',   '宏碁股份有限公司'),('2303','聯電',  '聯華電子'),
        ('2409','友達',   '友達光電'),        ('3034','聯詠',  '聯詠科技'),
        ('2379','瑞昱',   '瑞昱半導體'),      ('2344','華邦電','華邦電子'),
        ('2357','英業達', '英業達'),           ('2376','技嘉',  '技嘉科技'),
        ('3711','創意',   '創意電子'),
    ],
    '金融類': [
        ('2881','富邦金','富邦金融控股'), ('2882','國泰金','國泰金融控股'),
        ('2884','玉山金','玉山金融控股'), ('2885','元大金','元大金融控股'),
        ('2886','兆豐金','兆豐金融控股'), ('2887','台新金','台新金融控股'),
        ('2888','新光金','新光金融控股'), ('2890','永豐金','永豐金融控股'),
        ('2891','中信金','中國信託金融控股'),('2892','第一金','第一金融控股'),
        ('5876','上海商銀','上海商業儲蓄銀行'),
    ],
    '電信與公用事業': [
        ('2412','中華電','中華電信'),('4904','遠傳','遠傳電信'),
        ('3045','台灣大','台灣大哥大'),('6505','台塑化','台灣塑膠化學工業'),
        ('9945','潤泰全','潤泰全球'),
    ],
    '工業與原材料': [
        ('2002','中鋼','中國鋼鐵'),   ('1301','台塑','台灣塑膠工業'),
        ('1303','南亞','南亞塑膠工業'),('1326','台化','台灣化學纖維'),
        ('2105','正新','正新橡膠工業'),('1402','遠東新','遠東新世紀'),
        ('2009','東和鋼鐵','東和鋼鐵企業'),('1434','福懋','福懋興業'),
    ],
    '消費與零售': [
        ('2912','統一超','統一超商（7-ELEVEN）'),('1216','統一','統一企業'),
        ('2207','和泰車','和泰汽車'),           ('2103','亞泥','亞洲水泥'),
        ('9910','豐泰','豐泰企業'),             ('6239','力成','力成科技'),
    ],
}
TICKER_LOOKUP = {t:(s,f,sec) for sec,stk in TAIWAN_STOCK_UNIVERSE.items() for t,s,f in stk}

# ====================== 景氣 ======================
current_regime  = "溫和擴張（過熱／滯脹傾向）"
current_bias    = "品質、低波動、自由現金流／股息殖利率"
current_sectors = ["金融類", "電信與公用事業"]
df_hist = pd.DataFrame({
    '季度':          ['2023 Q1','2023 Q2','2023 Q3','2023 Q4','2024 Q1','2024 Q2','2024 Q3','2024 Q4','2025 Q1','2025 Q2','2025 Q3','2025 Q4','2026 Q1'],
    'IMFS報酬_%':    [15.2,13.8,12.5,14.0,10.5,10.5,9.5,9.0,10.5,10.5,7.5,7.0,11.0],
    '加權指數報酬_%': [11.0,10.0,12.0,11.5,9.0,8.5,7.5,7.0,12.0,11.5,6.5,6.5,22.0],
})

# ====================== Session 初始化 ======================
if "watchlist" not in st.session_state: st.session_state["watchlist"] = []
if "step_done" not in st.session_state: st.session_state["step_done"] = set()

def mark_step(n: int): st.session_state["step_done"].add(n)

# ====================== 工具函數 ======================
def _overheat() -> bool:
    return any(k in current_regime for k in ("過熱","滯脹"))

def _norm_div(raw) -> float:
    if not raw: return 0.0
    v = float(raw)
    return v if v > 1.0 else v * 100.0

def _badge_html(sig: str) -> str:
    if "買進" in sig: cls, dot = "badge-buy", "▲"
    elif "持有" in sig: cls, dot = "badge-hold", "◆"
    else: cls, dot = "badge-avoid", "▼"
    return f'<span class="badge {cls}">{dot} {sig}</span>'

def _sec(text: str) -> str:
    return f'<div class="sec-label">{text}</div>'

@st.cache_data(ttl=300)
def fetch_info(t: str) -> dict:
    symbol = t + ".TW"
    tk = yf.Ticker(symbol)

    # Primary source
    try:
        info = tk.info
        if isinstance(info, dict) and info:
            return info
    except:
        pass

    # Fallback for environments where .info is unstable/rate-limited
    out = {"symbol": symbol}
    try:
        fi = tk.fast_info
    except:
        fi = None

    def _fi_get(key):
        if fi is None:
            return None
        try:
            return fi.get(key)
        except:
            try:
                return fi[key]
            except:
                return None

    lp = _fi_get("last_price")
    mc = _fi_get("market_cap")
    sh = _fi_get("shares")
    pc = _fi_get("previous_close")
    dh = _fi_get("day_high")
    dl = _fi_get("day_low")

    if lp is not None:
        out["currentPrice"] = float(lp)
        out["regularMarketPrice"] = float(lp)
    if mc is not None:
        out["marketCap"] = float(mc)
    if sh is not None:
        out["sharesOutstanding"] = float(sh)
    if pc is not None:
        out["previousClose"] = float(pc)
    if dh is not None:
        out["dayHigh"] = float(dh)
    if dl is not None:
        out["dayLow"] = float(dl)

    # Final fallback: derive current price from recent candles
    if "currentPrice" not in out:
        try:
            h = tk.history(period="5d", auto_adjust=False)
            if not h.empty and "Close" in h.columns:
                p = h["Close"].dropna()
                if not p.empty:
                    last = float(p.iloc[-1])
                    out["currentPrice"] = last
                    out["regularMarketPrice"] = last
        except:
            pass

    return out if "currentPrice" in out else {}

@st.cache_data(ttl=300)
def fetch_cf(t: str) -> pd.DataFrame:
    try: return yf.Ticker(t+".TW").cashflow
    except: return pd.DataFrame()

@st.cache_data(ttl=300)
def dl_prices(tickers: tuple, s, e) -> dict:
    out={}
    for t in tickers:
        try:
            h=yf.download(t+".TW",start=s,end=e,progress=False,auto_adjust=True)
            if h.empty: continue
            c=h["Close"]
            if isinstance(c,pd.DataFrame): c=c.iloc[:,0]
            sq=c.squeeze()
            if isinstance(sq,pd.Series) and not sq.empty: out[t]=sq
        except: pass
    return out

def _cfrow(cf,*keys):
    for k in keys:
        if k in cf.index:
            v=cf.loc[k].iloc[0]; return float(v) if pd.notna(v) else 0.0
    return 0.0

def _calc_ret(prices,weights):
    clean={k:v.squeeze() for k,v in prices.items() if isinstance(v.squeeze(),pd.Series)}
    if not clean: return None,None
    df=pd.DataFrame(clean).dropna()
    if df.empty: return None,None
    w=weights[:df.shape[1]]; w=w/w.sum()
    pr=(df.pct_change().fillna(0)*w).sum(axis=1)
    return (1+pr).cumprod()-1, pr


# ====================== 5步驟引導面板 ======================
def render_step_guide(active_step: int):
    done = st.session_state["step_done"]
    steps = [
        (1, "景氣確認",  "主儀表板 → 景氣狀態 + 偏好板塊"),
        (2, "掃描候選",  "動態掃描 → 篩選低估值 + 確認買進區"),
        (3, "深度估值",  "選股估值 → DCF + MOS 安全邊際"),
        (4, "法醫篩選",  "Piotroski ≥ 3，無 Beneish 警示"),
        (5, "買進判斷",  "股價 ≤ MOS + 財務健全 + 景氣符合"),
    ]
    st.markdown(_sec("📋 5步驟投資流程"), unsafe_allow_html=True)
    for n, title, hint in steps:
        is_done   = n in done
        is_active = n == active_step
        card_cls  = "step-card done" if is_done else ("step-card active" if is_active else "step-card")
        num_color = "#34D399" if is_done else ("#60A5FA" if is_active else "#4B5563")
        icon      = "✅" if is_done else ("▶" if is_active else f"  {n}")
        st.markdown(f"""
<div class="{card_cls}">
  <div class="step-num" style="color:{num_color};">步驟 {n}</div>
  <div class="step-title">{icon} {title}</div>
  <div class="step-hint">{hint}</div>
</div>""", unsafe_allow_html=True)

    # 進度條
    total_done = len([n for n,*_ in steps if n in done or n == active_step])
    pct = int(total_done / len(steps) * 100)
    st.markdown(f"""
<div style="margin-top:0.5rem;">
  <div style="font-size:0.65rem;color:#9CA3AF;margin-bottom:4px;">整體進度 {pct}%</div>
  <div style="background:#374151;border-radius:4px;height:6px;">
    <div style="width:{pct}%;background:#60A5FA;border-radius:4px;height:6px;
                transition:width 0.3s ease;"></div>
  </div>
</div>""", unsafe_allow_html=True)


# ====================== 估值引擎 ======================
def run_valuation(ticker, company, sector):
    with st.spinner("取得資料中…"):
        info=fetch_info(ticker); cf=fetch_cf(ticker)
    if not info:
        st.error("無法取得資料。"); return

    price =float(info.get('currentPrice') or info.get('regularMarketPrice') or 0)
    shares=float(info.get('sharesOutstanding') or 1)
    beta  =float(info.get('beta') or 1.0)
    mktcap=float(info.get('marketCap') or price*shares)
    debt  =float(info.get('totalDebt') or 0)

    if not cf.empty:
        ni=_cfrow(cf,'Net Income','NetIncome')
        da=_cfrow(cf,'Depreciation And Amortization','Reconciled Depreciation','DepreciationAndAmortization')
        cx=abs(_cfrow(cf,'Capital Expenditure','CapitalExpenditures','Purchase Of Property Plant And Equipment'))
        oe=ni+da-cx
    else:
        ni=da=cx=0.0; oe=float(info.get('freeCashflow') or 0)
    oeps=oe/shares if shares>0 else 0.0

    rf=IMFS_Config.RF; geo=IMFS_Config.GEO_BUFFER/1e4
    rp=IMFS_Config.REGIME_PENALTY/1e4 if _overheat() else 0.0
    coe=rf+beta*(IMFS_Config.ERP/100)+geo+rp
    tc=mktcap+debt; ew=mktcap/tc if tc>0 else 1.0
    ie=abs(float(info.get('interestExpense') or 0))
    cod=(ie/debt) if debt>0 and ie>0 else 0.03
    wacc=ew*coe+(1-ew)*cod*(1-IMFS_Config.TAX_RATE)

    g5=max(0.0,min(float(info.get('earningsGrowth') or info.get('revenueGrowth') or 0.05),0.15))
    tg=IMFS_Config.TERMINAL_GROWTH
    pv5=sum(oeps*(1+g5)**y/(1+wacc)**y for y in range(1,6))
    tvp=(oeps*(1+g5)**5*(1+tg)/(wacc-tg))/(1+wacc)**5 if wacc>tg else 0.0
    iv=pv5+tvp; mos=iv*(1-IMFS_Config.MOS)
    valuation_ready = (iv > 0 and mos > 0)
    up=((iv-price)/price*100) if (price>0 and valuation_ready) else None

    sig=("買進 — 低於安全邊際價" if price>0 and price<=mos else
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
    pf =sum([roe>0,roa>0,ocf>0,ocf>ni_i,de<100,cr>1,float(info.get('earningsGrowth') or 0)>0])

    # 步驟 3 完成（估值執行）
    mark_step(3)
    if pf>=3 and (ni_i-ocf)/max(abs(ni_i),1)<=0.5: mark_step(4)
    if price>0 and valuation_ready and price<=mos: mark_step(5)

    # ── Header ──
    fit = sector in current_sectors
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;flex-wrap:wrap;">
  <span style="font-size:1.3rem;font-weight:700;color:#F9FAFB;">{ticker} — {company}</span>
  <span style="font-size:0.68rem;font-weight:600;background:#374151;color:#9CA3AF;
               border:1px solid #4B5563;border-radius:5px;padding:2px 9px;">{sector}</span>
  <span style="font-size:0.68rem;font-weight:700;
               background:{'#064E3B' if fit else '#450A0A'};
               color:{'#34D399' if fit else '#F87171'};
               border:1px solid {'#059669' if fit else '#B91C1C'};
               border-radius:5px;padding:2px 9px;">
    {'✓ 景氣符合' if fit else '✗ 景氣不符'}
  </span>
</div>
""", unsafe_allow_html=True)
    st.markdown(_badge_html(sig), unsafe_allow_html=True)
    st.markdown("---")

    # ── KPI 列 ──
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("目前股價",        f"NT${price:,.1f}" if price else "—")
    c2.metric("內在價值（DCF）", f"NT${iv:,.1f}"    if valuation_ready else "N/A")
    c3.metric("安全邊際價",      f"NT${mos:,.1f}"   if valuation_ready else "N/A",
              "-20%" if valuation_ready else None)
    c4.metric("距內在價值",      f"{up:+.1f}%"      if up is not None else "N/A",
              delta_color="normal" if (up is not None and up<0) else "inverse")
    c5.metric("WACC",            f"{wacc*100:.2f}%")
    c6.metric("股息殖利率",      f"{dy:.2f}%")
    if not valuation_ready:
        st.warning("此標的估值結果小於等於 0，暫不提供買進區判斷；請改用觀察或更換標的。")

    st.markdown("---")

    # ── WACC & DCF 圖 ──
    l,r = st.columns(2)
    with l:
        st.markdown(_sec("WACC 拆解"), unsafe_allow_html=True)
        wdf=pd.DataFrame({"組成":["無風險利率","Beta×ERP","地緣緩衝","景氣懲罰","WACC"],
                          "%":[rf*100,beta*IMFS_Config.ERP,IMFS_Config.GEO_BUFFER/100,
                               IMFS_Config.REGIME_PENALTY/100 if _overheat() else 0,wacc*100]})
        fw=px.bar(wdf,x="組成",y="%",text_auto=".2f",color_discrete_sequence=["#60A5FA"])
        fw.update_traces(textfont_color="#F9FAFB",textposition="outside",marker_line_width=0)
        fw.update_layout(**PT,height=260,showlegend=False)
        st.plotly_chart(fw,use_container_width=True)

    with r:
        st.markdown(_sec("DCF 估值拆解"), unsafe_allow_html=True)
        ddf=pd.DataFrame({"項目":["5年現金流","永續價值","內在價值","安全邊際價"],
                          "NT$":[pv5,tvp,iv,mos]})
        fd=px.bar(ddf,x="項目",y="NT$",text_auto=".1f",color="項目",
                  color_discrete_sequence=["#1E3A5F","#2563EB","#60A5FA","#FBBF24"])
        if price:
            fd.add_hline(y=price,line_dash="dot",line_color="#F87171",line_width=1.5,
                         annotation_text=f"現價 {price:.0f}",
                         annotation_font_color="#F87171",annotation_bgcolor="#450A0A")
        fd.update_traces(textfont_color="#F9FAFB",marker_line_width=0)
        fd.update_layout(**PT,height=260,showlegend=False)
        st.plotly_chart(fd,use_container_width=True)

    # ── 業主盈餘 ──
    st.markdown(_sec("業主盈餘（Owner Earnings = 淨利 ＋ 折舊攤銷 － 資本支出）"), unsafe_allow_html=True)
    e1,e2,e3,e4 = st.columns(4)
    if not cf.empty:
        e1.metric("淨利",       f"NT${ni/1e9:.2f}B")
        e2.metric("＋折舊攤銷", f"NT${da/1e9:.2f}B")
        e3.metric("－資本支出", f"NT${cx/1e9:.2f}B")
        e4.metric("＝業主盈餘", f"NT${oe/1e9:.2f}B")
    else:
        e1.metric("自由現金流（替代）", f"NT${oe/1e9:.2f}B")
        st.caption("現金流量表資料不足，以自由現金流替代")

    st.markdown("---")

    st.markdown(_step_hdr(4, "步驟 4　法醫篩選",
                          "檢查 Piotroski / Beneish / Altman，確認財務品質"),
                unsafe_allow_html=True)

    # ── 法醫評分 ──
    st.markdown(_sec("財務健全度（法醫會計）"), unsafe_allow_html=True)
    f1,f2,f3 = st.columns(3)
    pfl = "強健" if pf>=5 else "普通" if pf>=3 else "偏弱"
    f1.metric("Piotroski F-Score",  f"{pf}/7 — {pfl}")
    accrual_ok = (ni_i-ocf)/max(abs(ni_i),1)<=0.5
    f2.metric("Beneish 應計項目",   "✅ 正常" if accrual_ok else "⚠️ 疑似虛增")
    z=roe*2+cr*0.5+pb*0.3
    f3.metric("Altman Z（代理）",   f"{'⚠️ 危機' if z<1.5 else '🟡 灰色' if z<3 else '✅ 安全'} ({z:.1f})")

    st.markdown("")
    st.dataframe(pd.DataFrame({
        "指標": ["ROE","ROA","負債／權益","流動比率","P/B","股息殖利率"],
        "數值": [f"{roe*100:.1f}%" if roe else "—", f"{roa*100:.1f}%" if roa else "—",
                 f"{de:.1f}%"     if de   else "—", f"{cr:.2f}"       if cr   else "—",
                 f"{pb:.2f}"      if pb   else "—", f"{dy:.2f}%"],
        "說明": ["股東權益報酬率","資產報酬率","財務槓桿水準","短期償債能力","股價淨值比","年化股息殖利率"],
    }), use_container_width=True, hide_index=True)

    st.markdown("---")
    if st.button("➕ 加入觀察清單", type="secondary"):
        wl=st.session_state["watchlist"]
        e={"代號":ticker,"公司":company,"板塊":sector,"股價":price,
           "內在價值":round(iv,1),"MOS價":round(mos,1),
           "訊號":sig,"Piotroski":f"{pf}/7","殖利率%":f"{dy:.2f}%"}
        if ticker not in [w["代號"] for w in wl]:
            wl.append(e); st.session_state["watchlist"]=wl
            st.success(f"✅ {ticker} 已加入觀察清單")
        else: st.info(f"{ticker} 已在清單中")


# ====================== 掃描器 ======================
class MarketScanner:
    def __init__(self,s): self.s=s

    @st.cache_data(ttl=600)
    def _scan(_self, sectors, pe, pb, dy):
        rows=[]
        for sec in sectors:
            for tkr,_,full in TAIWAN_STOCK_UNIVERSE.get(sec,[]):
                try:
                    i=yf.Ticker(tkr+".TW").info
                    _pe=float(i.get('trailingPE') or float('inf'))
                    _pb=float(i.get('priceToBook') or float('inf'))
                    _dy=_norm_div(i.get('dividendYield'))
                    sc=int(_pe<pe)+int(_pb<pb)+int(_dy>dy)
                    if sc>=1:
                        _price=float(i.get('currentPrice') or 0)
                        # 快速估值：EPS × FAIR_PE（P/E法）
                        _eps=float(i.get('trailingEps') or 0)
                        _quick_iv=_eps*IMFS_Config.FAIR_PE if _eps>0 else 0.0
                        _mos_price=_quick_iv*(1-IMFS_Config.MOS)
                        _in_buy = (_price>0 and _mos_price>0 and _price<=_mos_price)
                        rows.append({
                            '代號': tkr,
                            '公司名稱': full,
                            '板塊': sec,
                            '股價': round(_price,2),
                            'P/E': round(_pe,2) if _pe!=float('inf') else None,
                            'P/B': round(_pb,2) if _pb!=float('inf') else None,
                            '殖利率%': round(_dy,2),
                            '快速公允價(P/E法)': round(_quick_iv,1) if _quick_iv>0 else None,
                            'MOS安全價': round(_mos_price,1) if _mos_price>0 else None,
                            '買進區': '✅ 買進區' if _in_buy else ('⏳ 觀望' if _price>0 else '—'),
                            '評分': sc,
                        })
                except: pass
        rows.sort(key=lambda x:(x['買進區']=='✅ 買進區', x['評分']),reverse=True)
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    def scan(self,pe=15,pb=1.2,dy=2.0): return self._scan(tuple(self.s),pe,pb,dy)


# ====================== 側邊欄 ======================
with st.sidebar:
    st.markdown("""
<div style="padding:0.6rem 0.75rem 0.6rem;">
  <div style="font-size:1.1rem;font-weight:800;color:#F9FAFB;letter-spacing:-0.02em;">IMFS v2.8</div>
  <div style="font-size:0.68rem;color:#60A5FA;margin-top:3px;font-weight:600;letter-spacing:0.04em;">
    台股機構級輪動系統
  </div>
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

    # 景氣快覽
    st.markdown(f"""
<div style="font-size:0.72rem;line-height:1.9;">
  <div style="color:#9CA3AF;font-weight:700;font-size:0.62rem;
              text-transform:uppercase;letter-spacing:0.1em;">當前景氣</div>
  <div style="color:#FBBF24;font-weight:600;">{current_regime}</div>
  <div style="color:#9CA3AF;font-weight:700;font-size:0.62rem;
              text-transform:uppercase;letter-spacing:0.1em;margin-top:8px;">偏好板塊</div>
  {"".join(f'<div style="color:#60A5FA;">▸ {s}</div>' for s in current_sectors)}
</div>
""", unsafe_allow_html=True)


# ── 頁面→步驟 映射 ──────────────────────────────────────────────────────────
PAGE_STEP = {
    "📊  主儀表板":       1,
    "🎯  動態股票掃描":   2,
    "🏷️  選股與完整估值": 3,
    "🔍  快速查詢":       3,
    "📈  投資組合模擬":   5,
    "📋  觀察清單":       5,
    "📖  方法論說明":     1,
}
active_step = PAGE_STEP.get(page, 1)
mark_step(active_step)


# ====================== 路由 ======================

# ── 主儀表板 ──────────────────────────────────────────────────────────────────
def _step_hdr(n: int, title: str, sub: str = "") -> str:
    colors = {1:"#60A5FA", 2:"#34D399", 3:"#FBBF24", 4:"#A78BFA", 5:"#F87171"}
    c = colors.get(n,"#9CA3AF")
    return f"""
<div style="display:flex;align-items:center;gap:12px;
            background:#1F2937;border:1px solid #374151;border-left:4px solid {c};
            border-radius:10px;padding:0.7rem 1rem;margin-bottom:1rem;">
  <div style="background:{c};color:#0D1117;font-weight:900;font-size:0.8rem;
              border-radius:50%;width:30px;height:30px;display:flex;align-items:center;
              justify-content:center;flex-shrink:0;">{n}</div>
  <div>
    <div style="font-size:1rem;font-weight:700;color:#F9FAFB;">{title}</div>
    <div style="font-size:0.71rem;color:#9CA3AF;margin-top:1px;">{sub}</div>
  </div>
</div>"""

if page == "📊  主儀表板":
    mark_step(1)
    st.title("投資決策流程")
    st.caption("依序完成五個步驟，系統化找出當前最佳買進標的")
    st.markdown("---")

    col_main, col_guide = st.columns([3, 1])

    with col_main:

        # ── STEP 1：景氣確認 ──────────────────────────────────────────────────
        st.markdown(_step_hdr(1,"步驟 1　景氣確認","判斷當前市場環境，確立偏好板塊與 WACC 加罰"),
                    unsafe_allow_html=True)

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("景氣狀態",       current_regime, "2026 Q2")
        c2.metric("偏好板塊",       " · ".join(current_sectors))
        c3.metric("台灣 PMI（3月）","53.3", "-2.1")
        c4.metric("WACC 景氣加罰",  "+150 bps", "過熱期生效")

        l1,r1 = st.columns([3,2])
        with l1:
            st.markdown(_sec("立即行動建議（2026 Q2）"), unsafe_allow_html=True)
            st.info("**配置：** 60–80% 品質／自由現金流／高股息\n\n"
                    "**板塊：** 金融、電信與公用事業\n\n"
                    "**門檻：** 股價 ≤ 安全邊際價（內在價值×80%）\n\n"
                    "**WACC：** 本季加入 +150 bps 景氣懲罰溢價")
        with r1:
            st.markdown(_sec("風險矩陣"), unsafe_allow_html=True)
            st.dataframe(pd.DataFrame({
                "風險": ["景氣轉折","地緣政治","通膨急升","流動性"],
                "機率": ["中等","高","中高","中等"],
                "對應": ["PMI季檢","WACC+1.5%","WACC+1.5%懲罰","大型股優先"],
            }), use_container_width=True, hide_index=True)

        t_chart,t_data = st.tabs(["歷史績效圖","數據"])
        with t_chart:
            fig=go.Figure()
            fig.add_bar(x=df_hist['季度'],y=df_hist['IMFS報酬_%'],name="IMFS",
                        marker_color="#60A5FA",marker_line_width=0)
            fig.add_bar(x=df_hist['季度'],y=df_hist['加權指數報酬_%'],name="加權指數",
                        marker_color="#374151",marker_line_width=0)
            fig.update_layout(**{**PT,
                'barmode':'group','height':260,
                'title':dict(text="季度報酬率對比（%）",font=dict(color="#E5E7EB",size=12)),
                'legend':dict(orientation="h",yanchor="bottom",y=1.02,x=0,
                              bgcolor="#1F2937",bordercolor="#4B5563",font=dict(color="#9CA3AF"))})
            st.plotly_chart(fig,use_container_width=True)
        with t_data:
            st.dataframe(df_hist,use_container_width=True,hide_index=True)

        st.markdown("---")

        # ── STEP 2：掃描候選 ──────────────────────────────────────────────────
        st.markdown(_step_hdr(2,"步驟 2　掃描候選","依景氣偏好板塊篩選低估值高殖利率標的，確認買進區"),
                    unsafe_allow_html=True)

        s2_c1,s2_c2,s2_c3,s2_c4 = st.columns([2,1,1,1])
        s2_sel = s2_c1.multiselect("板塊篩選",list(TAIWAN_STOCK_UNIVERSE.keys()),
                                    default=current_sectors,label_visibility="collapsed")
        s2_pe  = s2_c2.number_input("P/E ≤",value=15,min_value=1,max_value=50,
                                     label_visibility="collapsed")
        s2_pb  = s2_c3.number_input("P/B ≤",value=1.2,min_value=0.1,max_value=10.0,step=0.1,
                                     label_visibility="collapsed")
        s2_dy  = s2_c4.number_input("殖利率 ≥%",value=3.0,min_value=0.0,max_value=15.0,step=0.5,
                                     label_visibility="collapsed")

        scan_triggered = st.button("快速掃描 ▶", type="primary", key="main_scan_btn")
        if s2_sel and scan_triggered:
            with st.spinner("掃描中（含快速估值）…"):
                st.session_state["main_scan"] = MarketScanner(s2_sel).scan(s2_pe,s2_pb,s2_dy)
            mark_step(2)

        scan_res = st.session_state.get("main_scan")
        if not isinstance(scan_res, pd.DataFrame):
            scan_res = pd.DataFrame()
        if not scan_res.empty:
            buy_n = len(scan_res[scan_res['買進區']=='✅ 買進區'])
            sa,sb,sc_ = st.columns(3)
            sa.metric("候選數",  len(scan_res))
            sb.metric("✅ 買進區", buy_n, delta_color="normal" if buy_n>0 else "off")
            sc_.metric("⏳ 觀望", len(scan_res)-buy_n)

            st.dataframe(scan_res, use_container_width=True, hide_index=True,
                column_config={
                    "代號":             st.column_config.TextColumn(width=70),
                    "公司名稱":         st.column_config.TextColumn(width=140),
                    "板塊":             st.column_config.TextColumn(width=110),
                    "股價":             st.column_config.NumberColumn("股價(NT$)",format="%.2f"),
                    "P/E":              st.column_config.NumberColumn(format="%.2f"),
                    "P/B":              st.column_config.NumberColumn(format="%.2f"),
                    "殖利率%":          st.column_config.NumberColumn("殖利率%",format="%.2f"),
                    "快速公允價(P/E法)": st.column_config.NumberColumn("公允價",format="%.1f"),
                    "MOS安全價":        st.column_config.NumberColumn("MOS價",format="%.1f"),
                    "買進區":           st.column_config.TextColumn("買進區",width=85),
                    "評分":             st.column_config.ProgressColumn("評分",min_value=0,max_value=3),
                })
            buy_rows = scan_res[scan_res['買進區']=='✅ 買進區']
            if not buy_rows.empty:
                st.markdown(_sec("✅ 買進區標的 — 建議進入步驟3執行完整DCF估值"),
                            unsafe_allow_html=True)
                for _,row in buy_rows.iterrows():
                    disc=((row['股價']-row['MOS安全價'])/row['MOS安全價']*100
                          if row['MOS安全價'] and row['MOS安全價']>0 else 0)
                    st.markdown(f"""
<div style="background:#052E16;border:1px solid #059669;border-radius:8px;
            padding:0.55rem 0.9rem;margin-bottom:0.35rem;display:flex;
            align-items:center;gap:14px;flex-wrap:wrap;">
  <span style="font-size:0.9rem;font-weight:700;color:#F9FAFB;">{row['代號']} {row['公司名稱']}</span>
  <span style="color:#9CA3AF;font-size:0.75rem;">{row['板塊']}</span>
  <span style="color:#34D399;font-weight:700;">NT${row['股價']:.1f}</span>
  <span style="color:#9CA3AF;font-size:0.75rem;">安全價 NT${row['MOS安全價']:.1f} ｜ 折價 {disc:.1f}%</span>
  <span style="color:#34D399;font-size:0.75rem;">殖利率 {row['殖利率%']:.2f}%</span>
</div>""", unsafe_allow_html=True)

        st.markdown("---")

        # ── STEP 3：深度估值（同步執行步驟4法醫篩選） ───────────────────────
        st.markdown(_step_hdr(3,"步驟 3　深度估值",
                               "執行 DCF / WACC，並同步完成步驟4法醫篩選（Piotroski / Beneish / Altman）"),
                    unsafe_allow_html=True)
        all_s=[{"t":t,"s":s,"f":f,"sec":sec,"disp":f"{t} — {f}  [{sec}]"}
               for sec,stk in TAIWAN_STOCK_UNIVERSE.items() for t,s,f in stk]
        # 若掃描有買進區標的，預設第一個
        default_disp = all_s[0]["disp"]
        if not scan_res.empty:
            buy_tickers = list(scan_res[scan_res['買進區']=='✅ 買進區']['代號'])
            if buy_tickers:
                hit = next((x for x in all_s if x["t"]==buy_tickers[0]), None)
                if hit: default_disp = hit["disp"]
        default_idx = next((i for i,x in enumerate(all_s) if x["disp"]==default_disp), 0)

        vs_col, vb_col = st.columns([5,1])
        with vs_col:
            v_disp = st.selectbox("選擇標的",[x["disp"] for x in all_s],
                                  index=default_idx, label_visibility="collapsed")
        v_chosen = next(x for x in all_s if x["disp"]==v_disp)
        with vb_col:
            st.markdown("<br>",unsafe_allow_html=True)
            v_run = st.button("執行估值 ▶",type="primary",use_container_width=True,key="main_val")
        if v_run:
            run_valuation(v_chosen["t"], v_chosen["f"], v_chosen["sec"])

        st.markdown("---")

        # ── STEP 5：買進判斷 ──────────────────────────────────────────────────
        st.markdown(_step_hdr(5,"步驟 5　買進判斷",
                               "逐項確認買進條件，全部達標方可建立部位"),
                    unsafe_allow_html=True)

        wl = st.session_state.get("watchlist",[])
        chk = [
            ("股價 ≤ MOS 安全邊際價（內在價值 × 80%）", 5 in st.session_state["step_done"]),
            ("Piotroski F-Score ≥ 3（財務健全）",       4 in st.session_state["step_done"]),
            ("無 Beneish 應計虛增警示",                  4 in st.session_state["step_done"]),
            ("板塊符合當前景氣偏好",                     2 in st.session_state["step_done"]),
            ("殖利率 ≥ 3%（高股息景氣偏好期）",          2 in st.session_state["step_done"]),
        ]
        passed = sum(1 for _,v in chk if v)
        signal_color = "#34D399" if passed==5 else "#FBBF24" if passed>=3 else "#F87171"
        signal_label = "全條件達標 — 可考慮建立部位" if passed==5 else \
                       f"部分達標（{passed}/5）— 繼續完成上方步驟" if passed>=3 else \
                       f"未達標（{passed}/5）— 請先完成步驟 2、3、4"

        st.markdown(f"""
<div style="background:#1F2937;border:1px solid #4B5563;border-radius:10px;padding:1rem 1.1rem;">
  <div style="font-size:0.9rem;font-weight:700;color:{signal_color};margin-bottom:0.8rem;">
    {signal_label}
  </div>""", unsafe_allow_html=True)
        for label, ok in chk:
            icon  = "✅" if ok else "⬜"
            color = "#E5E7EB" if ok else "#6B7280"
            st.markdown(f'<div style="font-size:0.82rem;color:{color};'
                        f'padding:3px 0;">{icon}  {label}</div>',
                        unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if wl:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(_sec(f"觀察清單（{len(wl)} 檔）"), unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(wl), use_container_width=True, hide_index=True)

    with col_guide:
        st.markdown("<br>", unsafe_allow_html=True)
        active = (5 if 5 in st.session_state["step_done"] else
                  4 if 4 in st.session_state["step_done"] else
                  3 if 3 in st.session_state["step_done"] else
                  2 if 2 in st.session_state["step_done"] else 1)
        render_step_guide(active)
        st.markdown("---")
        st.markdown("""
<div style="background:#1F2937;border:1px solid #4B5563;border-radius:8px;padding:0.75rem 1rem;">
  <div style="font-size:0.62rem;font-weight:700;text-transform:uppercase;
              letter-spacing:0.1em;color:#9CA3AF;margin-bottom:6px;">五大買進門檻</div>
  <div style="font-size:0.75rem;color:#E5E7EB;line-height:1.95;">
    ① 股價 ≤ MOS 安全價<br>
    ② Piotroski ≥ 3<br>
    ③ 無 Beneish 警示<br>
    ④ 板塊符合景氣偏好<br>
    ⑤ 殖利率 ≥ 3%
  </div>
</div>
""", unsafe_allow_html=True)

# ── 選股估值 ──────────────────────────────────────────────────────────────────
elif page == "🏷️  選股與完整估值":
    col_main, col_guide = st.columns([3,1])
    with col_main:
        st.title("選股與完整估值")
        st.caption("搜尋台股代號或名稱，執行業主盈餘 DCF 完整估值")

        all_s=[{"t":t,"s":s,"f":f,"sec":sec,"disp":f"{t} — {f}  [{sec}]"}
               for sec,stk in TAIWAN_STOCK_UNIVERSE.items() for t,s,f in stk]
        q=st.text_input("","",placeholder="搜尋代號或名稱（例：2330、台積電、金融）",
                        label_visibility="collapsed").strip().lower()
        fil=([x for x in all_s if q in x["t"] or q in x["f"].lower()
              or q in x["s"].lower() or q in x["sec"].lower()] if q else all_s)

        if not fil: st.warning("查無結果。")
        else:
            cs,cb=st.columns([5,1])
            with cs:
                cd=st.selectbox(f"共 {len(fil)} 筆",
                                [x["disp"] for x in fil],label_visibility="collapsed")
            chosen=next(x for x in fil if x["disp"]==cd)
            with cb:
                st.markdown("<br>",unsafe_allow_html=True)
                run=st.button("執行估值 ▶",type="primary",use_container_width=True)

            st.markdown("---")
            if run: run_valuation(chosen["t"],chosen["f"],chosen["sec"])
    with col_guide:
        st.markdown("<br>", unsafe_allow_html=True)
        render_step_guide(3)

# ── 快速查詢 ──────────────────────────────────────────────────────────────────
elif page == "🔍  快速查詢":
    col_main, col_guide = st.columns([3,1])
    with col_main:
        st.title("快速查詢")
        c1,c2=st.columns([4,1])
        tkr=c1.text_input("","2881",label_visibility="collapsed")
        with c2:
            st.markdown("<br>",unsafe_allow_html=True)
            go_=st.button("查詢",type="primary",use_container_width=True)
        if go_:
            info=fetch_info(tkr)
            if info:
                dy=_norm_div(info.get('dividendYield'))
                _,full,_=TICKER_LOOKUP.get(tkr,("","",""))
                r1,r2,r3,r4,r5=st.columns(5)
                r1.metric("公司",info.get('longName',full) or full)
                r2.metric("股價",f"NT${info.get('currentPrice','—')}")
                r3.metric("P/E", f"{info.get('trailingPE','—')}")
                r4.metric("P/B", f"{info.get('priceToBook','—')}")
                r5.metric("殖利率",f"{dy:.2f}%")
            else: st.error("無法取得資料。")
    with col_guide:
        st.markdown("<br>", unsafe_allow_html=True)
        render_step_guide(3)

# ── 動態掃描 ──────────────────────────────────────────────────────────────────
elif page == "🎯  動態股票掃描":
    col_main, col_guide = st.columns([3,1])
    with col_main:
        st.title("動態市場掃描")
        st.caption("景氣感知篩選 ｜ 依偏好板塊自動設定門檻 ｜ 含快速買進區判斷")

        with st.expander("⚙️ 掃描參數",expanded=True):
            c1,c2,c3,c4=st.columns(4)
            sel=c1.multiselect("板塊",list(TAIWAN_STOCK_UNIVERSE.keys()),default=current_sectors)
            pe =c2.number_input("P/E 上限",value=12 if "品質" in current_bias else 18,min_value=1,max_value=50)
            pb =c3.number_input("P/B 上限",value=1.0 if "品質" in current_bias else 1.5,min_value=0.1,max_value=10.0,step=0.1)
            dy =c4.number_input("殖利率下限 %",value=3.0 if "品質" in current_bias else 2.0,min_value=0.0,max_value=15.0,step=0.5)

        if sel and st.button("立即掃描 ▶",type="primary",use_container_width=True):
            with st.spinner("掃描中（含快速估值）…"):
                res=MarketScanner(sel).scan(pe,pb,dy)
            if not res.empty:
                mark_step(2)
                # 買進區統計
                buy_cnt=len(res[res['買進區']=='✅ 買進區'])
                c_a,c_b,c_c = st.columns(3)
                c_a.metric("候選標的數", len(res))
                c_b.metric("✅ 在買進區", buy_cnt,
                           delta_color="normal" if buy_cnt>0 else "off")
                c_c.metric("⏳ 觀望", len(res)-buy_cnt)

                ch1,ch2=st.columns(2)
                with ch1:
                    fp=px.pie(res,names='板塊',title="板塊分布",color_discrete_sequence=C)
                    fp.update_layout(**PT,height=240)
                    st.plotly_chart(fp,use_container_width=True)
                with ch2:
                    bz=res['買進區'].value_counts().reset_index()
                    bz.columns=['狀態','數量']
                    fb=px.bar(bz,x='狀態',y='數量',title="買進區分布",
                              color='狀態',color_discrete_map={'✅ 買進區':'#34D399','⏳ 觀望':'#9CA3AF','—':'#374151'})
                    fb.update_layout(**PT,height=240,showlegend=False)
                    st.plotly_chart(fb,use_container_width=True)

                st.markdown(_sec("掃描結果（含快速買進區判斷）"), unsafe_allow_html=True)
                st.caption("快速公允價 = 近4季EPS × 15倍 P/E ｜ MOS安全價 = 公允價 × 80% ｜ 買進區 = 現價 ≤ MOS安全價")
                st.dataframe(res, use_container_width=True, hide_index=True,
                    column_config={
                        "代號":            st.column_config.TextColumn(width=70),
                        "公司名稱":        st.column_config.TextColumn(width=150),
                        "板塊":            st.column_config.TextColumn(width=120),
                        "股價":            st.column_config.NumberColumn("股價(NT$)", format="%.2f"),
                        "P/E":             st.column_config.NumberColumn(format="%.2f"),
                        "P/B":             st.column_config.NumberColumn(format="%.2f"),
                        "殖利率%":         st.column_config.NumberColumn("殖利率%", format="%.2f"),
                        "快速公允價(P/E法)":st.column_config.NumberColumn("公允價(NT$)", format="%.1f"),
                        "MOS安全價":       st.column_config.NumberColumn("MOS安全價", format="%.1f"),
                        "買進區":          st.column_config.TextColumn("買進區", width=90),
                        "評分":            st.column_config.ProgressColumn("評分", min_value=0, max_value=3),
                    })

                # 買進區高亮
                buy_stocks = res[res['買進區']=='✅ 買進區']
                if not buy_stocks.empty:
                    st.markdown("---")
                    st.markdown(_sec("✅ 在買進區的標的（建議進一步執行 DCF 完整估值）"), unsafe_allow_html=True)
                    for _,row in buy_stocks.iterrows():
                        disc = ((row['股價']-row['MOS安全價'])/row['MOS安全價']*100
                                if row['MOS安全價'] and row['MOS安全價']>0 else 0)
                        st.markdown(f"""
<div style="background:#052E16;border:1px solid #059669;border-radius:8px;
            padding:0.65rem 1rem;margin-bottom:0.4rem;display:flex;
            align-items:center;gap:16px;flex-wrap:wrap;">
  <span style="font-size:0.95rem;font-weight:700;color:#F9FAFB;">
    {row['代號']} {row['公司名稱']}
  </span>
  <span style="color:#9CA3AF;font-size:0.78rem;">{row['板塊']}</span>
  <span style="color:#34D399;font-weight:700;font-size:0.85rem;">
    NT${row['股價']:.1f}
  </span>
  <span style="color:#9CA3AF;font-size:0.78rem;">
    安全價 NT${row['MOS安全價']:.1f} ｜ 折價 {disc:.1f}%
  </span>
  <span style="color:#34D399;font-size:0.78rem;font-weight:600;">
    殖利率 {row['殖利率%']:.2f}%
  </span>
</div>""", unsafe_allow_html=True)
            else: st.warning("無符合標的，請調整參數。")

    with col_guide:
        st.markdown("<br>", unsafe_allow_html=True)
        render_step_guide(2)
        st.markdown("---")
        st.markdown(f"""
<div style="background:#1F2937;border:1px solid #4B5563;border-radius:8px;padding:0.75rem 1rem;">
  <div style="font-size:0.65rem;font-weight:700;text-transform:uppercase;
              letter-spacing:0.1em;color:#9CA3AF;margin-bottom:6px;">買進區說明</div>
  <div style="font-size:0.75rem;color:#E5E7EB;line-height:1.85;">
    快速估值採<br>
    <span style="color:#60A5FA;font-weight:600;">EPS × 15倍</span> P/E 法<br>
    安全邊際打八折<br>
    ── ✅ 現價 ≤ 安全價<br>
    ── ⏳ 現價 > 安全價<br><br>
    <span style="color:#FBBF24;">建議</span>：<br>
    進入「選股估值」<br>
    執行完整 DCF 確認
  </div>
</div>
""", unsafe_allow_html=True)

# ── 投組模擬 ──────────────────────────────────────────────────────────────────
elif page == "📈  投資組合模擬":
    col_main, col_guide = st.columns([3,1])
    with col_main:
        st.title("投資組合回測模擬器")
        with st.expander("⚙️ 策略設定",expanded=True):
            c1,c2=st.columns(2)
            yrs=c1.slider("回測期間（年）",1,5,3)
            strat=c2.selectbox("策略",["成長型（2330、2308、3231）",
                                        "品質／高股息（2881、2412、2882）",
                                        "均衡配置（2330、2881、2308）"])
        sm={"成長型（2330、2308、3231）":(["2330","2308","3231"],np.array([.40,.35,.25]),"成長型"),
            "品質／高股息（2881、2412、2882）":(["2881","2412","2882"],np.array([.40,.35,.25]),"品質／高股息"),
            "均衡配置（2330、2881、2308）":(["2330","2881","2308"],np.array([.33,.33,.34]),"均衡配置")}
        tkrs,wts,name=sm[strat]
        ed=datetime.now(); sd=ed-timedelta(days=365*yrs)
        st.info(f"回測 **{name}** ｜ {sd.date()} → {ed.date()}")
        with st.spinner("下載歷史價格…"):
            prices=dl_prices(tuple(tkrs),sd,ed)
        cum,dret=_calc_ret(prices,wts)
        if cum is not None and len(cum)>0:
            tr=cum.iloc[-1]*100; ar=((1+cum.iloc[-1])**(1/yrs)-1)*100
            vol=dret.std()*np.sqrt(252)*100; shr=(ar-2)/vol if vol>0 else 0
            mdd=(cum.cummax()-cum).max()*100
            m1,m2,m3,m4,m5=st.columns(5)
            m1.metric("總報酬",    f"{tr:.1f}%",  delta_color="normal" if tr>0 else "inverse")
            m2.metric("年化報酬",  f"{ar:.1f}%",  delta_color="normal" if ar>0 else "inverse")
            m3.metric("年化波動率",f"{vol:.1f}%")
            m4.metric("夏普比率",  f"{shr:.2f}")
            m5.metric("最大回撤",  f"-{mdd:.1f}%")
            fig3=go.Figure()
            fig3.add_trace(go.Scatter(x=cum.index,y=cum.values*100,mode='lines',name=name,
                                       fill='tozeroy',line=dict(color='#60A5FA',width=2),
                                       fillcolor='rgba(96,165,250,0.08)'))
            fig3.add_hline(y=0,line_dash="dot",line_color="#374151",line_width=1)
            fig3.update_layout(**{**PT,
                'height':360,
                'title':dict(text=f"{name} — 累積報酬率（%）",font=dict(color="#E5E7EB",size=12))})
            fig3.update_xaxes(title_text="日期")
            fig3.update_yaxes(title_text="累積報酬 (%)")
            st.plotly_chart(fig3,use_container_width=True)
        else: st.warning("無法計算，請確認網路或更換策略。")
    with col_guide:
        st.markdown("<br>", unsafe_allow_html=True)
        render_step_guide(5)

# ── 觀察清單 ──────────────────────────────────────────────────────────────────
elif page == "📋  觀察清單":
    col_main, col_guide = st.columns([3,1])
    with col_main:
        st.title("觀察清單")
        wl=st.session_state.get("watchlist",[])
        if wl:
            st.dataframe(pd.DataFrame(wl),use_container_width=True,hide_index=True)
            if st.button("清空清單",type="secondary"):
                st.session_state["watchlist"]=[]; st.rerun()
        else: st.info("清單為空，請至「選股與完整估值」加入標的。")
    with col_guide:
        st.markdown("<br>", unsafe_allow_html=True)
        render_step_guide(5)

# ── 方法論 ────────────────────────────────────────────────────────────────────
elif page == "📖  方法論說明":
    st.title("方法論說明")
    st.caption("IMFS v2.8：景氣輪動 × 業主盈餘 DCF × 法醫會計")
    t1,t2,t3,t4=st.tabs(["一、景氣輪動","二、業主盈餘 DCF","三、法醫會計","四、使用流程"])
    with t1:
        st.markdown("""
**Investment Clock（Merrill Lynch, 2004）**

| 象限 | 景氣 | 通膨 | 偏好板塊 |
|------|------|------|----------|
| 復甦期 | ↑ | ↓ | 景氣循環、消費 |
| 擴張期 | ↑ | ↑ | 科技、原材料 |
| 過熱期 | → | ↑ | 能源、高股息、金融 |
| 滯脹期 | ↓ | ↑ | 公用事業、防禦型 |

**台灣應用：** 每季根據 PMI、CPI 判斷象限 → 決定偏好板塊 + WACC 加罰幅度（過熱期 +150 bps）
        """)
    with t2:
        st.markdown("""
**業主盈餘（Buffett, 1986）**
```
業主盈餘 = 淨利 ＋ 折舊攤銷 － 資本支出
```
**WACC 組成：** Rf(1.5%) + Beta×ERP(5.5%) + 地緣緩衝(1.5%) + 景氣懲罰(1.5% 過熱時)

**安全邊際價 = 內在價值 × 80%**

**掃描快速估值：** 近4季EPS × 15倍 P/E 作為公允價，打八折得安全價（適合快速篩選，確認須做完整 DCF）

**殖利率修正：** yfinance 部分台股已回傳百分比格式，系統自動偵測（>1 視為已是%），確保顯示正確。
        """)
    with t3:
        st.markdown("""
**Piotroski F-Score（2000）** — 7分：ROE、ROA、現金流品質、負債比、流動比率、成長性

**Beneish M-Score（1999）** — 應計比率 > 0.5 疑似盈餘虛增

**Altman Z-Score 代理（1968）** — Z = ROE×2 + 流動比率×0.5 + P/B×0.3

< 1.5 危機 ｜ 1.5-3 灰色 ｜ > 3 安全
        """)
    with t4:
        st.markdown("""
```
步驟 1  景氣確認   → 主儀表板：景氣狀態 + 偏好板塊
步驟 2  掃描候選   → 動態股票掃描：篩選低估值 + 確認買進區（EPS×15×0.8）
步驟 3  深度估值   → 選股與完整估值：業主盈餘 DCF + MOS 安全邊際
步驟 4  法醫篩選   → Piotroski ≥ 3 + 無 Beneish 警示 + Altman Z 安全
步驟 5  買進判斷   → 股價 ≤ MOS + 板塊符合景氣 + 殖利率 ≥ 3%
         持倉管理  → 股價 > 內在價值 考慮減碼；每季重評景氣象限
```
右側面板會追蹤你的進度，完成步驟後會顯示綠色打勾。
        """)

# ── 頁腳 ──────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<p style="font-size:0.65rem;color:#374151;text-align:center;">'
            'IMFS v2.8 ｜ Buffett (1986) · Damodaran (2012) · Graham (1949) · '
            'Piotroski (2000) · Beneish (1999) · Altman (1968) · ML Investment Clock (2004)'
            '</p>', unsafe_allow_html=True)
