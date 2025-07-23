import streamlit as st              # Streamlit for building the web app UI
import requests                      # requests for HTTP calls to external APIs
import pandas as pd                  # pandas for data manipulation and tabular structures
import matplotlib.pyplot as plt      # matplotlib for creating charts
import numpy as np                  # NumPy for numerical operations
from dotenv import load_dotenv
import os

# API key for Financial Modeling Prep; used in URL construction for data fetches
load_dotenv()
apikey = os.getenv("FMP_API_KEY")

def get_fcf(ticker):
    """
    Fetch the last 5 years of free cash flow for a given ticker.
    Returns a pandas Series indexed by date, values in billions.
    """
    # Construct URL for cash flow statement endpoint with ticker and API key
    url = f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{ticker}?limit=5&apikey={apikey}"
    res = requests.get(url)                      # HTTP GET request
    if res.status_code != 200:                    # Check for successful response
        return None                               # Return None to indicate error
    data = res.json()                             # Parse JSON response into Python list/dict
    # Validate presence of freeCashFlow field in first entry
    if not data or "freeCashFlow" not in data[0]:
        return None
    # Build a Series: keys = date strings, values = freeCashFlow values
    fcf_series = pd.Series({entry["date"]: entry["freeCashFlow"] for entry in data})
    fcf_series = fcf_series.sort_index()          # Ensure dates are in ascending order
    fcf_series = fcf_series / 1e9                 # Convert raw cash flow to billions
    return fcf_series                             # Return the cleaned Series

def get_quote_data(ticker):
    """
    Fetch current quote data for a given ticker.
    Returns a dict with fields like 'price' and 'sharesOutstanding'.
    """
    url = f"https://financialmodelingprep.com/api/v3/quote/{ticker}?apikey={apikey}"
    res = requests.get(url)                       # HTTP GET request
    if res.status_code != 200:                    # Check for successful response
        return None
    data = res.json()                             # Parse JSON into Python
    return data[0] if data else None              # Return first quote or None

def discount(values, rate):
    """
    Discount a list of cash flow values by a constant rate.
    values: list of future cash flows
    rate: discount rate (decimal)
    Returns list of discounted cash flows.
    """
    # For each cash flow v at time i+1, apply v / (1 + rate)^(i+1)
    return [v / ((1 + rate) ** (i + 1)) for i, v in enumerate(values)]

def run_dcf_with_data(fcf_series, quote, wacc, terminal_growth, growths):
    """
    Run a 5-year DCF given historical FCF, market quote, WACC, terminal growth,
    and list of annual growth rates.
    Returns a dict of valuation outputs.
    """
    latest_fcf = fcf_series.values[-1]            # Most recent free cash flow
    projected_fcfs = []                           # Container for future FCF projections
    fcf = latest_fcf                              # Initialize projection with latest FCF

    # Project FCF for each year using the provided growth rates
    for g in growths:
        fcf *= (1 + g)                            # Apply growth
        projected_fcfs.append(fcf)                # Store projected value

    # Calculate Terminal Value using Gordon growth model
    terminal_value = projected_fcfs[-1] * (1 + terminal_growth) / (wacc - terminal_growth)
    # Discount projected FCFs to present value
    discounted_fcfs = discount(projected_fcfs, wacc)
    # Discount the terminal value back 5 years
    discounted_tv = terminal_value / ((1 + wacc) ** len(projected_fcfs))
    # Enterprise Value = sum of discounted FCFs + discounted terminal value
    enterprise_value = sum(discounted_fcfs) + discounted_tv

    shares = quote["sharesOutstanding"] / 1e9     # Convert shares to billions
    fair_value = enterprise_value / shares        # Per-share fair value
    price = quote["price"]                        # Current market price
    upside = ((fair_value - price) / price) * 100 # Percentage upside/(downside)

    # Package all results into a dict for easy access
    result = {
        "enterprise_value": enterprise_value,
        "fair_value": fair_value,
        "price": price,
        "upside": upside,
        "fcf_projection": projected_fcfs,
        "discounted_fcfs": discounted_fcfs,
        "terminal_value": terminal_value,
        "discounted_terminal_value": discounted_tv
    }
    return result

# === Streamlit App UI ===

st.title("Monte Carlo DCF Valuation")  
# Title appears at top in large font for immediate context

st.markdown(
    "This tool runs a Monte Carlo simulation of 5-year DCF valuations "
    "using randomized input ranges."
)
# Markdown for descriptive text below the title—allows **bold**, links, etc.

ticker = st.text_input("Enter ticker symbol (e.g. AAPL):").upper()
# Text input widget; `.upper()` normalizes input to uppercase tickers

if ticker:  # Proceed only if user has entered a ticker
    fcf_series = get_fcf(ticker)      # Fetch FCF history
    quote_data = get_quote_data(ticker)  # Fetch current quote

    # Error state: show message if data fetch failed or insufficient history
    if fcf_series is None or quote_data is None or len(fcf_series) < 3:
        st.error("Could not fetch data or insufficient FCF history.")
    else:
        # Calculate historical CAGR of FCF for use as Monte Carlo mean
        fcf_start = fcf_series.iloc[0]
        fcf_end = fcf_series.iloc[-1]
        years = len(fcf_series)
        cagr = ((fcf_end / fcf_start) ** (1 / (years - 1))) - 1

        st.subheader("Simulation Parameters")
        # Subheader groups the input controls under a clear label

        # Number of Monte Carlo runs
        n_simulations = st.slider(
            "Number of Simulations", 100, 5000, 1000, step=100
        )

        st.markdown("**Growth Rate**")  # Bold markdown to label growth rate inputs
        growth_std = st.slider(
            "Growth Rate Std Dev", 0.0, 0.2, 0.05, 0.005
        )

        st.markdown("**WACC**")  # Label for weighted average cost of capital inputs
        wacc = st.slider(
            "WACC Mean", 0.01, 0.20, 0.09, 0.01
        )
        wacc_std = st.slider(
            "WACC Std Dev", 0.0, 0.1, 0.01, 0.005
        )

        st.markdown("**Terminal Growth Rate**")
        terminal_growth = st.slider(
            "Terminal Growth Mean", 0.0, 0.10, 0.025, 0.005
        )
        tg_std = st.slider(
            "Terminal Growth Std Dev", 0.0, 0.05, 0.005, 0.001
        )

        # Button triggers the Monte Carlo simulation when clicked
        if st.button("Run Monte Carlo Simulation"):
            fair_values = []  # Collect fair values from each run
            sim_outputs = []  # Store full simulation output dicts

            # Run simulations
            for _ in range(n_simulations):
                # Sample growth, WACC, terminal growth from normal distributions
                g = np.random.normal(cagr, growth_std)
                w = np.clip(
                    np.random.normal(wacc, wacc_std), 0.01, 0.25
                )  # Constrain WACC to [1%,25%]
                tg = np.clip(
                    np.random.normal(terminal_growth, tg_std), 0.0, 0.10
                )  # Constrain terminal growth to [0%,10%]
                growths_sim = [g] * 5  # Same growth each year for simplicity

                try:
                    sim_result = run_dcf_with_data(
                        fcf_series, quote_data, w, tg, growths_sim
                    )
                    fair_values.append(sim_result["fair_value"])
                    sim_outputs.append(sim_result)
                except:
                    # Skip any runs that error out (e.g. division by zero)
                    continue

            if fair_values:  # Only proceed if at least one simulation succeeded
                # Compute summary statistics
                mean_fv = np.mean(fair_values)
                closest_idx = np.argmin(np.abs(np.array(fair_values) - mean_fv))
                representative = sim_outputs[closest_idx]

                st.subheader("Simulation Summary")
                # Write key metrics to the app
                st.write(f"**Mean Fair Value:** ${mean_fv:.2f}")
                st.write(f"**Median Fair Value:** ${np.median(fair_values):.2f}")
                st.write(
                    f"**10–90th Percentile:** "
                    f"${np.percentile(fair_values, 10):.2f} – "
                    f"${np.percentile(fair_values, 90):.2f}"
                )
                st.write(
                    f"**Upside/Downside:** "
                    f"{(mean_fv - representative['price']) / representative['price'] * 100:.2f}%"
                )

                st.subheader("Cash Flow Forecast (Representative Simulation)")
                # Build a DataFrame for the representative run
                df = pd.DataFrame({
                    "Year": [f"Year {i+1}" for i in range(5)],
                    "Projected FCF": representative["fcf_projection"],
                    "Discounted FCF": representative["discounted_fcfs"]
                })
                st.dataframe(df.set_index("Year"))  # Display as an interactive table

                st.subheader("Valuation Chart")
                # Create a bar chart comparing projected vs discounted FCF
                fig, ax = plt.subplots()
                ax.bar(df["Year"], df["Projected FCF"], alpha=0.6, label="Projected FCF")
                ax.bar(df["Year"], df["Discounted FCF"], alpha=0.6, label="Discounted FCF")
                ax.set_ylabel("Billions")      # Y-axis label
                ax.legend()                    # Show legend to distinguish bars
                ax.set_title("FCF Projection & Discounting")
                # Annotate terminal value on the chart
                ax.annotate(
                    f"Terminal Value: ${representative['discounted_terminal_value']:.2f}B",
                    xy=(4, representative['discounted_terminal_value'] * 0.9),
                    fontsize=10,
                    color="green"
                )
                st.pyplot(fig)  # Render the chart in Streamlit

                st.subheader("Distribution of Fair Values")
                # Histogram of all simulated fair values
                fig2, ax2 = plt.subplots()
                ax2.hist(fair_values, bins=50, edgecolor="black")
                ax2.set_title("Monte Carlo Fair Value Distribution")
                ax2.set_xlabel("Fair Value")
                ax2.set_ylabel("Frequency")
                st.pyplot(fig2)  # Render the histogram