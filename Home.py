import streamlit as st

st.set_page_config(page_title="Finance Toolkit", page_icon="📊", layout="centered")

st.title("Finance Toolkit")
st.markdown("""
Welcome to **Harry Canty’s** finance toolkit. Use the sidebar to open apps.
""")

c1, c2 = st.columns(2)
with c1:
    st.header("DCF Valuation")
    st.write("Monte Carlo FCFF DCF with Equity conversion and distribution analysis.")
    st.page_link("pages/DCF_Valuation.py", label="Open DCF App", icon="➡️")
with c2:
    st.header("Black–Scholes")
    st.write("European option pricing with Greeks and clean formatting.")
    st.page_link("pages/BS_Calculator.py", label="Open Options App", icon="➡️")
