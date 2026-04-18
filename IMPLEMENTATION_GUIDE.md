# IMFS v2.3 Implementation Guide

## 1. Overview

IMFS v2.3 is an institutional-grade equity valuation framework for the Taiwan stock market. It combines quantitative analysis with macroeconomic regime detection to deliver consistent alpha through dynamic sector rotation and automatic stock discovery.

**Key Objectives:**
- Deliver +4% to +7% annualized alpha over 5-year periods
- Reduce drawdowns during market downturns
- Automate stock discovery within selected sectors
- Provide forensic accounting analysis

---

## 2. Core Logic & Methodology

### 2.1 Regime Detection System
- **Taiwan PMI (Purchasing Managers Index)**: Economic expansion indicator
- **Market volatility**: Risk assessment
- **Geopolitical buffer (+150 bps)**: Taiwan-specific risk premium

**Current Regime (April 2026):** Mild Expansion with Overheat/Stagflation Tilt
- **Factor Bias:** Quality, Low Volatility, Free Cash Flow / Dividend Yield
- **Recommended Sectors:** Financials, Utilities

### 2.2 Valuation Framework

**For Financials:**
- ROE (Return on Equity) analysis
- P/TBV (Price-to-Tangible Book Value)
- Dividend yield assessment
- NPA (Non-Performing Assets) ratios

**For Technology:**
- P/E relative to growth rate
- Free cash flow margins
- Capital intensity & ROIC
- Revenue growth momentum

**For Utilities:**
- FCF yield analysis
- Dividend sustainability
- Regulatory environment
- Debt/EBITDA ratios

### 2.3 Forensic Accounting Checks
- **Altman Z-Score** (solvency)
- **Beneish M-Score** (earnings manipulation)
- **Piotroski F-Score** (financial quality)

**Margin of Safety:** 15-25% discount to intrinsic value

---

## 3. Dashboard Components

### 3.1 Main Dashboard
- Real-time regime display with PMI indicator
- Risk matrix showing key risk factors
- Quarterly performance tracking (IMFS vs TAIEX)
- Action items based on current regime

### 3.2 Ticker Valuation Engine
- Manual ticker input for individual stock analysis
- Real-time price fetching from yfinance
- Quick valuation assessment with investment signals
- Forensic analysis recommendations

### 3.3 Dynamic Stock Scanner (NEW)
**Purpose:** Automatically discover 5-8 undervalued stocks per sector

**Process:**
1. User selects target sectors (Tech, Finance, Utilities, Industrials)
2. System scans all available stocks in those sectors
3. Screens based on:
   - P/E ratio < threshold (regime-adjusted: 12 for quality, 18 for growth)
   - P/B ratio < 1.0-1.5 (regime-adjusted)
   - Dividend yield > 2-3% (regime-adjusted)
4. Returns ranked list of top candidates

**Screening Thresholds by Regime:**
- **Quality/Defensive:** P/E < 12, Div Yield > 3%
- **Growth/Expansion:** P/E < 18, Div Yield > 2%

### 3.4 Portfolio Simulator
- Real historical data backtesting (1-5 years)
- Three pre-built strategies:
  - Growth (2330, 2308, 3131)
  - Quality/Dividend (2881, 8926, 2072)
  - Balanced Mix
- Risk metrics: Volatility, Sharpe ratio, max drawdown
- Visual performance charts

---

## 4. Technical Implementation

### 4.1 Architecture
