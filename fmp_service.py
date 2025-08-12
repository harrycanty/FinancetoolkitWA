# fmp_service.py
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter, Retry

# ---------- config ----------
load_dotenv()
API_KEY = os.getenv("FMP_API_KEY", "")
BASE_URL = "https://financialmodelingprep.com/api/v3"


# creates cached requets to help with api only having 250 pulls daily, cache is deleted after an hour
@st.cache_resource
def _session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
    )
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s

# helper for get requests to api
def _get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    if params is None:
        params = {}
    if API_KEY:
        params.setdefault("apikey", API_KEY)
    else:
        st.warning("FMP_API_KEY not set; requests may fail.", icon="⚠️")

    url = f"{BASE_URL}/{path.lstrip('/')}"
    r = _session().get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

# gets historical fcf for given ticket
@st.cache_data(ttl=3600)
def get_fcf(ticker: str, limit: int = 8) -> Optional[pd.Series]:
    
    if not ticker:
        return None
    try:
        data: List[Dict[str, Any]] = _get(f"cash-flow-statement/{ticker}", {"limit": limit})
        if not data:
            return None
        df = pd.DataFrame(data)
        if not {"date", "freeCashFlow"}.issubset(df.columns):
            return None
        ser = (
            pd.Series(df["freeCashFlow"].values, index=pd.to_datetime(df["date"]), name="FCF")
            .sort_index()
        )
        return ser
    except Exception as e:
        st.error(f"get_fcf error: {e}")
        return None


@st.cache_data(ttl=600)

# gets latest quote price for given ticker
def get_quote_data(ticker: str) -> Optional[pd.Series]:
   
    if not ticker:
        return None
    try:
        data: List[Dict[str, Any]] = _get(f"quote/{ticker}")
        if not data:
            return None
        row = data[0]
        ser = pd.Series(row, name=ticker)
        return ser
    except Exception as e:
        st.error(f"get_quote_data error: {e}")
        return None


@st.cache_data(ttl=3600)

# gets historiccal balance sheet data for given ticker
def get_balance_sheet(ticker: str, limit: int = 8) -> Optional[pd.DataFrame]:
    
    if not ticker:
        return None
    try:
        data: List[Dict[str, Any]] = _get(f"balance-sheet-statement/{ticker}", {"limit": limit})
        if not data:
            return None
        df = pd.DataFrame(data)
        if "date" not in df.columns:
            return None
        df.index = pd.to_datetime(df["date"])
        df = df.sort_index()
        return df
    except Exception as e:
        st.error(f"get_balance_sheet error: {e}")
        return None