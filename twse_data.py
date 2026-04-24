import json
import ssl
from urllib.request import Request, urlopen

import streamlit as st


BASE_URL = "https://openapi.twse.com.tw/v1"

INCOME_ENDPOINTS = [
    "/opendata/t187ap06_L_ci",
    "/opendata/t187ap06_L_basi",
    "/opendata/t187ap06_L_fh",
    "/opendata/t187ap06_L_ins",
    "/opendata/t187ap06_L_bd",
    "/opendata/t187ap06_L_mim",
]

BALANCE_ENDPOINTS = [
    "/opendata/t187ap07_L_ci",
    "/opendata/t187ap07_L_basi",
    "/opendata/t187ap07_L_fh",
    "/opendata/t187ap07_L_ins",
    "/opendata/t187ap07_L_bd",
    "/opendata/t187ap07_L_mim",
]


def _request_json(path: str):
    req = Request(
        BASE_URL + path,
        headers={
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "If-Modified-Since": "Mon, 26 Jul 1997 05:00:00 GMT",
        },
    )
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8-sig"))
    except Exception:
        # TWSE occasionally presents a cert chain that some Python runtimes reject.
        insecure = ssl.create_default_context()
        insecure.check_hostname = False
        insecure.verify_mode = ssl.CERT_NONE
        with urlopen(req, timeout=30, context=insecure) as resp:
            return json.loads(resp.read().decode("utf-8-sig"))


def _clean_text(v):
    if v is None:
        return ""
    return str(v).strip()


def _clean_float(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "").replace("%", "")
    if s in {"", "--", "---", "N/A", "NA", "null", "None"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _clean_int(v):
    f = _clean_float(v)
    if f is None:
        return None
    return int(f)


def _pick(row, *keys):
    for key in keys:
        if key in row and _clean_text(row[key]) != "":
            return row[key]
    return None


def _pick_contains(row, *fragments):
    for key, value in row.items():
        if all(fragment in key for fragment in fragments) and _clean_text(value) != "":
            return value
    return None


def _row_code(row):
    return _clean_text(
        _pick(row, "公司代號", "Code", "證券代號", "股票代號", "代號")
    )


def _report_sort_key(row):
    year = _clean_int(_pick(row, "年度")) or 0
    quarter = _clean_int(_pick(row, "季別")) or 0
    date = _clean_text(_pick(row, "出表日期", "Date"))
    return (year, quarter, date)


def _latest_by_code(rows):
    latest = {}
    for row in rows:
        code = _row_code(row)
        if not code:
            continue
        if code not in latest or _report_sort_key(row) > _report_sort_key(latest[code]):
            latest[code] = row
    return latest


@st.cache_data(ttl=3600)
def _fetch_rows(path: str):
    data = _request_json(path)
    return data if isinstance(data, list) else []


@st.cache_data(ttl=3600)
def _company_basics():
    return {_row_code(row): row for row in _fetch_rows("/opendata/t187ap03_L") if _row_code(row)}


@st.cache_data(ttl=3600)
def _bwibbu_all():
    return {_row_code(row): row for row in _fetch_rows("/exchangeReport/BWIBBU_ALL") if _row_code(row)}


@st.cache_data(ttl=3600)
def _stock_day_all():
    return {_row_code(row): row for row in _fetch_rows("/exchangeReport/STOCK_DAY_ALL") if _row_code(row)}


@st.cache_data(ttl=3600)
def _monthly_revenue():
    return _latest_by_code(_fetch_rows("/opendata/t187ap05_L"))


@st.cache_data(ttl=3600)
def _dividend_data():
    rows = _fetch_rows("/opendata/t187ap45_L")
    latest = {}
    for row in rows:
        code = _row_code(row)
        if not code:
            continue
        year = _clean_int(_pick(row, "股利年度")) or 0
        quarter = _clean_int(_pick(row, "股利所屬年(季)度")) or 0
        progress = _clean_text(_pick(row, "決議（擬議）進度"))
        sort_key = (year, quarter, progress)
        if code not in latest or sort_key > latest[code][0]:
            latest[code] = (sort_key, row)
    return {code: pair[1] for code, pair in latest.items()}


@st.cache_data(ttl=3600)
def _income_latest():
    rows = []
    for path in INCOME_ENDPOINTS:
        rows.extend(_fetch_rows(path))
    return _latest_by_code(rows)


@st.cache_data(ttl=3600)
def _balance_latest():
    rows = []
    for path in BALANCE_ENDPOINTS:
        rows.extend(_fetch_rows(path))
    return _latest_by_code(rows)


@st.cache_data(ttl=3600)
def build_twse_snapshot(code: str):
    code = _clean_text(code)
    if not code:
        return {}

    basics = _company_basics().get(code, {})
    bwi = _bwibbu_all().get(code, {})
    day = _stock_day_all().get(code, {})
    revenue = _monthly_revenue().get(code, {})
    dividend = _dividend_data().get(code, {})
    income = _income_latest().get(code, {})
    balance = _balance_latest().get(code, {})

    out = {}

    company_name = _clean_text(_pick(basics, "公司簡稱", "公司名稱"))
    industry = _clean_text(_pick(basics, "產業別"))
    shares = _clean_float(_pick(basics, "已發行普通股數或TDR原股發行股數"))
    price = _clean_float(_pick(day, "ClosingPrice"))
    price_date = _clean_text(_pick(day, "Date"))
    pb = _clean_float(_pick(bwi, "PBratio"))
    pe = _clean_float(_pick(bwi, "PEratio"))
    dy = _clean_float(_pick(bwi, "DividendYield"))

    if company_name:
        out["longName"] = company_name
        out["shortName"] = company_name
    if industry:
        out["_twse_industry"] = industry
    if shares and shares > 0:
        out["sharesOutstanding"] = shares
    if price and price > 0:
        out["currentPrice"] = price
        out["regularMarketPrice"] = price
        out["_last_close"] = price
        out["_last_close_date"] = price_date
        out["_price_source"] = "twse_stock_day_all"
    if pb is not None:
        out["priceToBook"] = pb
    if dy is not None:
        out["dividendYield"] = dy
    if pe is not None and pe > 0:
        out["trailingPE"] = pe
    if price and pe and pe > 0:
        out["trailingEps"] = price / pe

    cash_div = _clean_float(
        _pick(dividend, "股東配發-盈餘分配之現金股利(元/股)")
    )
    if "dividendYield" not in out and cash_div and price and price > 0:
        out["dividendYield"] = cash_div / price * 100.0

    revenue_yoy = _clean_float(_pick(revenue, "營業收入-去年同月增減(%)"))
    revenue_mom = _clean_float(_pick(revenue, "營業收入-上月比較增減(%)"))
    if revenue_yoy is not None:
        out["revenueGrowth"] = revenue_yoy / 100.0
    if revenue_mom is not None:
        out["_revenue_growth_mom"] = revenue_mom / 100.0
    revenue_value = _clean_float(_pick(revenue, "營業收入-當月營收"))
    if revenue_value is not None:
        out["_monthly_revenue"] = revenue_value

    total_assets = _clean_float(_pick(balance, "資產總額"))
    total_liabilities = _clean_float(_pick(balance, "負債總額"))
    equity = _clean_float(_pick(balance, "歸屬於母公司業主之權益合計", "權益總額"))
    current_assets = _clean_float(_pick(balance, "流動資產"))
    current_liabilities = _clean_float(_pick(balance, "流動負債"))
    book_value_per_share = _clean_float(_pick(balance, "每股參考淨值"))

    if total_assets is not None:
        out["_total_assets"] = total_assets
    if total_liabilities is not None:
        out["_total_liabilities"] = total_liabilities
    if equity is not None:
        out["_total_equity"] = equity
    if current_assets is not None:
        out["_current_assets"] = current_assets
    if current_liabilities is not None:
        out["_current_liabilities"] = current_liabilities
    if book_value_per_share is not None:
        out["_book_value_per_share"] = book_value_per_share
    if current_assets is not None and current_liabilities and current_liabilities > 0:
        out["currentRatio"] = current_assets / current_liabilities
    if total_liabilities is not None and equity and equity > 0:
        out["debtToEquity"] = total_liabilities / equity * 100.0

    eps_latest = _clean_float(_pick_contains(income, "基本每股盈餘"))
    if "trailingEps" not in out and eps_latest is not None and eps_latest > 0:
        out["trailingEps"] = eps_latest * 4.0

    revenue_total = _clean_float(_pick(income, "營業收入"))
    operating_income = _clean_float(_pick_contains(income, "營業利益"))
    if revenue_total is not None:
        out["_quarterly_revenue"] = revenue_total
    if operating_income is not None:
        out["_quarterly_operating_income"] = operating_income

    ttm_eps = _clean_float(out.get("trailingEps"))
    if ttm_eps is not None and ttm_eps > 0 and shares and shares > 0:
        ttm_net_income = ttm_eps * shares
        out["netIncomeToCommon"] = ttm_net_income
        if book_value_per_share and book_value_per_share > 0:
            out["returnOnEquity"] = ttm_eps / book_value_per_share
            if total_liabilities is not None and equity and equity > 0:
                leverage = total_liabilities / equity
                asset_per_share = book_value_per_share * (1.0 + leverage)
                if asset_per_share > 0:
                    out["returnOnAssets"] = ttm_eps / asset_per_share

    if price and shares and shares > 0:
        out["marketCap"] = price * shares

    if out:
        out["_twse_snapshot_ready"] = True
        out["_twse_sources"] = [
            "t187ap03_L",
            "STOCK_DAY_ALL",
            "BWIBBU_ALL",
            "t187ap05_L",
            "t187ap06_L_*",
            "t187ap07_L_*",
            "t187ap45_L",
        ]
    return out
