import pandas as pd
from black_scholes import BS
import streamlit as st

st.title("📈 Black-Scholes Option Pricing Tool")

# Inputs
col1, col2 = st.columns(2)
with col1:
    spot = st.number_input("Spot Price", value=100.0)
    strike = st.number_input("Strike Price", value=100.0)
    rate = st.number_input("Risk-Free Rate (as decimal)", value=0.05, format="%.4f")
with col2:
    days = st.number_input("Days to Expiry", value=30)
    volatility = st.number_input("Volatility (as decimal)", value=0.2, format="%.4f")
    multiplier = st.number_input("Option Multiplier", value=100)

# Calculation
if st.button("Calculate"):
    try:
        model = BS(spot, strike, rate, days, volatility, multiplier)
        
        data = {
            "Call": [
                model.call_price(),
                model.call_delta(),
                model.call_gamma(),
                model.call_vega(),
                model.call_theta(),
                model.call_rho()
            ],
            "Put": [
                model.put_price(),
                model.put_delta(),
                model.put_gamma(),
                model.put_vega(),
                model.put_theta(),
                model.put_rho()  
            ]
        }

        index = ["Price", "Delta", "Gamma", "Vega", "Theta", "Rho"]
        df = pd.DataFrame(data, index=index)

        st.subheader("📊 Option Pricing & Greeks")
        st.dataframe(df.style.format("{:.4f}"))

    except Exception as e:
        st.error(f"Calculation failed: {e}")