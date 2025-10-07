import os
import json
from datetime import date, timedelta
from typing import List, Dict, Any, Optional

import requests
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

def cache_path_for() -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    # usa el archivo más reciente si existe, o el nombre por defecto
    default = os.path.join(DATA_DIR, "rates_cache.csv")
    # si hay otros caches, retorna el más nuevo
    candidates = [os.path.join(DATA_DIR, p) for p in os.listdir(DATA_DIR) if p.endswith(".csv")]
    if candidates:
        return sorted(candidates, key=os.path.getmtime)[-1]
    return default

def fetch_timeseries(start_date: str, end_date: str, base: str="USD", symbols: Optional[List[str]]=None) -> Dict[str, Any]:
    params = {"start_date": start_date, "end_date": end_date, "base": base}
    if symbols:
        params["symbols"] = ",".join(symbols)

    url = "https://api.exchangerate.host/timeseries"
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    # Si la API no trae datos, cortamos con mensaje claro
    rates = data.get("rates")
    if not isinstance(rates, dict) or len(rates) == 0:
        raise ValueError("La API no devolvió datos (revisá códigos y rango de fechas).")

    from .process import tidy_rates
    df = tidy_rates(data, base=base)
    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(os.path.join(DATA_DIR, "rates_cache.csv"), index=False)
    return data


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch exchange rate timeseries and cache as CSV.")
    parser.add_argument("--days", type=int, default=90, help="Número de días hacia atrás desde hoy.")
    parser.add_argument("--base", type=str, default="USD", help="Moneda base.")
    parser.add_argument("--symbols", type=str, default="EUR,GBP,JPY,MXN,ARS,BRL,CLP,COP", help="Lista separada por comas.")
    args = parser.parse_args()

    end = date.today()
    start = end - timedelta(days=args.days)
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]

    print(f"Descargando {start} → {end} | base={args.base} | symbols={symbols}")
    data = fetch_timeseries(start.isoformat(), end.isoformat(), base=args.base, symbols=symbols)
    print("OK: cache actualizado en", cache_path_for())
