import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

from fmp_service import get_fcf, get_quote_data, get_balance_sheet
from core_dcf import run_dcf_vectorized

st.title("Monte Carlo DCF Valuation (FCFF)")

# --- Input ticker ---
ticker = st.text_input("Ticker (e.g., AAPL)", placeholder="AAPL").strip().upper()
if not ticker:
    st.stop()

# --- Fetch data ---
with st.spinner("Fetching data..."):
    fcf_series = get_fcf(ticker)              # Expect raw USD values from API
    quote = get_quote_data(ticker)            # Dict with price, sharesOutstanding
    bs = get_balance_sheet(ticker)            # DataFrame, newest row first

if (fcf_series is None) or (quote is None) or (len(fcf_series) < 3):
    st.error("Could not fetch data or insufficient FCF history (need ≥3 years).")
    st.stop()

# --- Ensure oldest → newest ordering for CAGR ---
if fcf_series.index[0] > fcf_series.index[-1]:
    fcf_series = fcf_series[::-1]

# --- Calculate CAGR from oldest to newest ---
fcf_start, fcf_end = fcf_series.iloc[0], fcf_series.iloc[-1]
years = len(fcf_series)
cagr = (fcf_end / fcf_start) ** (1 / (years - 1)) - 1 if years > 1 and fcf_start > 0 else 0.05

# --- Simulation parameter controls ---
st.subheader("Simulation Parameters")
c1, c2, c3 = st.columns(3)
with c1:
    n_sim = st.slider("Simulations", 500, 20000, 5000, step=500)
    seed = st.number_input("Random Seed (optional)", value=0, min_value=0)
with c2:
    wacc_mean = st.slider("WACC Mean", 0.02, 0.20, 0.09, 0.005)
    wacc_std  = st.slider("WACC Std Dev", 0.000, 0.10, 0.015, 0.005)
with c3:
    tg_mean = st.slider("Terminal Growth Mean", 0.000, 0.050, 0.025, 0.001)
    tg_std  = st.slider("Terminal Growth Std Dev", 0.000, 0.020, 0.005, 0.001)

g1, g2 = st.columns(2)
with g1:
    growth_mean = st.slider("Annual FCF Growth Mean", -0.50, 0.50, float(np.round(cagr, 4)), 0.005)
with g2:
    growth_std  = st.slider("Annual FCF Growth Std Dev", 0.00, 0.30, 0.06, 0.005)

if tg_mean >= wacc_mean:
    st.warning("Terminal growth should be less than WACC for a finite terminal value.")

# --- Run simulation ---
if st.button("Run Monte Carlo"):
    with st.spinner("Simulating..."):
        sim = run_dcf_vectorized(
            last_fcf_bil=fcf_series.iloc[-1] / 1e9,  # Convert to billions if model expects billions
            n=n_sim,
            wacc_mean=wacc_mean, wacc_std=wacc_std,
            tg_mean=tg_mean, tg_std=tg_std,
            growth_mean=growth_mean, growth_std=growth_std,
            seed=None if seed == 0 else int(seed),
        )

    # 1. EV from simulation in USD
    ev_usd = np.asarray(sim["ev"], dtype=float) * 1e9

    # 2. Cash & debt in USD (latest row)
    if isinstance(bs, pd.DataFrame) and not bs.empty:
        cash_col = bs.get("cashAndShortTermInvestments")
        debt_col = bs.get("totalDebt")
        cash_usd = float(cash_col.iloc[0]) if cash_col is not None and not cash_col.empty else 0.0
        debt_usd = float(debt_col.iloc[0]) if debt_col is not None and not debt_col.empty else 0.0
    else:
        cash_usd, debt_usd = 0.0, 0.0

    # 3. Equity value in USD
    equity_val_usd = ev_usd + cash_usd - debt_usd

    # 4. Shares outstanding (raw)
    shares_out = float(quote.get("sharesOutstanding", 0.0))
    if shares_out <= 0:
        st.error("Invalid or missing shares outstanding.")
        st.stop()

    # 5. Fair value per share (USD)
    fair_values = equity_val_usd / shares_out
    price = float(quote.get("price", float("nan")))

    # --- Tabs for output ---
    tabs = st.tabs(["Summary", "Forecast (rep path)", "Distribution"])

    with tabs[0]:
        mean_fv = np.nanmean(fair_values)
        median_fv = np.nanmedian(fair_values)
        p10, p90 = np.nanpercentile(fair_values, [10, 90])

        m1, m2, m3 = st.columns(3)
        m1.metric("Mean Fair Value", f"${mean_fv:,.2f}")
        m2.metric("Median Fair Value", f"${median_fv:,.2f}")
        m3.metric("P10 – P90", f"${p10:,.2f} – ${p90:,.2f}")

        if np.isfinite(price):
            up = (mean_fv - price) / price * 100
            st.metric("Upside vs Price", f"{up:.2f}%")
            st.caption(f"Ref price: ${price:,.2f}")

        st.download_button(
            "Download Fair Values (CSV)",
            data=pd.Series(fair_values, name="fair_value").to_csv(index=False).encode(),
            file_name=f"{ticker}_fair_values.csv",
            mime="text/csv",
        )

    with tabs[1]:
        idx = int(np.nanargmin(np.abs(fair_values - np.nanmean(fair_values))))
        df = pd.DataFrame({
            "Year": [f"Year {i+1}" for i in range(5)],
            "Projected FCF (B)": sim["fcf"][idx],
            "Discounted FCF (B)": sim["disc_fcf"][idx],
        }).set_index("Year")
        st.dataframe(df.style.format("{:,.2f}"))
        st.write(f"Discounted Terminal Value (B): **{sim['tv_disc'][idx]:,.2f}**")

    with tabs[2]:
        fig, ax = plt.subplots()
        ax.hist(fair_values[~np.isnan(fair_values)], bins=60, edgecolor="black")
        ax.set_title("Fair Value Distribution")
        ax.set_xlabel("Fair Value (per share)")
        ax.set_ylabel("Frequency")
        st.pyplot(fig)
