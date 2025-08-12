import pandas as pd
import streamlit as st
from black_scholes import BS

st.title("Black–Scholes Option Pricing Tool")

# ---- Helpers ----
def fmt_money(x: float) -> str: return f"€{x:,.2f}"
def fmt_small(x: float) -> str: return f"{x:.4f}"
def fmt_pct(x: float) -> str:   return f"{x*100:.2f}%"

with st.form(key="bs_inputs"):
    col1, col2 = st.columns(2)
    with col1:
        spot = st.number_input("Spot Price", value=100.0, min_value=0.0, help="Underlying price")
        strike = st.number_input("Strike Price", value=95.0, min_value=0.0)
        rate = st.number_input("Risk‑Free Rate (annual, decimal)", value=0.05, format="%.4f", step=0.0001)
    with col2:
        days = st.number_input("Days to Expiry (calendar)", value=30, min_value=1, step=1)
        volatility = st.number_input("Volatility (annual, decimal)", value=0.20, format="%.4f", min_value=0.0001, step=0.0001)
        multiplier = st.number_input("Contract Multiplier", value=100, min_value=1, step=1)

    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        theta_basis = st.selectbox("Theta basis", ["per year", "per day (÷365)"], index=1)
    with c2:
        dp = st.number_input("Decimals (table)", value=4, min_value=2, max_value=6, step=1)
    submitted = st.form_submit_button("Calculate")

if submitted:
    try:
        model = BS(spot, strike, rate, days, volatility, multiplier)

        # Compute shared greeks once
        gamma = model.gamma()
        vega = model.vega()

        # Theta basis
        theta_div = 365.0 if theta_basis.startswith("per day") else 1.0

        data = {
            "Call": [
                model.call_price(),
                model.call_delta(),
                gamma,
                vega,
                model.call_theta() / theta_div,
                model.call_rho()
            ],
            "Put": [
                model.put_price(),
                model.put_delta(),
                gamma,
                vega,
                model.put_theta() / theta_div,
                model.put_rho()
            ],
        }
        index = ["Price", "Delta", "Gamma", "Vega", "Theta", "Rho"]
        df = pd.DataFrame(data, index=index)

        st.subheader("📊 Option Pricing & Greeks")
        # Column formatting
        formats = {
            "Price": fmt_money,
            "Delta": fmt_small,
            "Gamma": fmt_small,
            "Vega":  fmt_small,
            "Theta": fmt_small,
            "Rho":   fmt_small,
        }
        styled = df.style.format({col: (formats[idx] if idx in formats else "{:.4f}")
                                  for idx, col in zip(df.index, ["Call","Put"])}, na_rep="–")
        st.dataframe(df.style.format({c: f"{{:.{dp}f}}" for c in df.columns}))

        # Quick stats row
        c1, c2, c3 = st.columns(3)
        c1.metric("Call Price", fmt_money(df.loc["Price","Call"]))
        c2.metric("Put Price",  fmt_money(df.loc["Price","Put"]))
        c3.metric("Put–Call Δ", fmt_money(df.loc["Price","Put"] - df.loc["Price","Call"]))


    except Exception as e:
        st.error(f"Calculation failed: {e}")
