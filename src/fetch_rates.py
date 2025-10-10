# src/fetch_rates.py
import os
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
import requests
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def cache_path_for() -> str:
    _ensure_data_dir()
    candidates = [os.path.join(DATA_DIR, p) for p in os.listdir(DATA_DIR) if p.endswith(".csv")]
    if candidates:
        return sorted(candidates, key=os.path.getmtime)[-1]
    return os.path.join(DATA_DIR, "rates_cache.csv")


def _timestamped_path() -> str:
    _ensure_data_dir()
    return os.path.join(DATA_DIR, f"rates_{date.today().isoformat()}.csv")


def _fetch_frankfurter(start_date: str, end_date: str, base: str, symbols: Optional[List[str]]) -> Dict[str, Any]:
    to = ",".join(symbols) if symbols else ""
    url = f"https://api.frankfurter.app/{start_date}..{end_date}?from={base}"
    if to:
        url += f"&to={to}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    if "rates" in data and isinstance(data["rates"], dict):
        return {"rates": data["rates"], "base": base}
    return {"rates": {}, "base": base}


def fetch_timeseries(start_date: str, end_date: str, base: str = "USD", symbols: Optional[List[str]] = None) -> Dict[str, Any]:
    try:
        data = _fetch_frankfurter(start_date, end_date, base, symbols)
        rates = data.get("rates")
        if isinstance(rates, dict) and len(rates) > 0:
            from .process import tidy_rates
            df = tidy_rates(data, base=base)
            if df.empty:
                raise ValueError("No se generaron filas a partir de frankfurter.app.")
            df.to_csv(_timestamped_path(), index=False)
            return data
        raise ValueError("La API Frankfurter no devolvió datos.")
    except Exception as e:
        raise ValueError(f"Error descargando series: {e}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch exchange rate timeseries and cache as CSV.")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--base", type=str, default="USD")
    parser.add_argument("--symbols", type=str, default="EUR,GBP,JPY,MXN,ARS,BRL,CLP,COP")
    args = parser.parse_args()

    end = date.today()
    start = end - timedelta(days=args.days)
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    print(f"Descargando {start} → {end} | base={args.base} | symbols={symbols}")
    data = fetch_timeseries(start.isoformat(), end.isoformat(), base=args.base.upper(), symbols=symbols)
    print("OK: cache actualizado en", cache_path_for())
