from typing import Dict, Any
import pandas as pd
import numpy as np

def tidy_rates(payload: Dict[str, Any], base: str) -> pd.DataFrame:
    rates = payload.get("rates", {})
    # Si la API no trae datos, devolvemos DF vacío con columnas esperadas
    if not isinstance(rates, dict) or len(rates) == 0:
        return pd.DataFrame(columns=["date", "base", "symbol", "rate"])

    rows = []
    for d, symbols in rates.items():
        if not isinstance(symbols, dict):
            continue
        for sym, value in symbols.items():
            rows.append({
                "date": pd.to_datetime(d),
                "base": base,
                "symbol": str(sym),
                "rate": float(value),
            })
    if not rows:
        return pd.DataFrame(columns=["date", "base", "symbol", "rate"])

    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)

def add_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["symbol", "date"]).copy()
    # Variación diaria por símbolo
    df["pct_change"] = df.groupby("symbol")["rate"].pct_change() * 100.0
    # Media móvil 7 días y desviación
    df["ma7"] = df.groupby("symbol")["rate"].transform(lambda s: s.rolling(window=7, min_periods=3).mean())
    df["std7"] = df.groupby("symbol")["rate"].transform(lambda s: s.rolling(window=7, min_periods=3).std())
    # Z-score simple sobre pct_change
    def zscore(s: pd.Series) -> pd.Series:
        m = s.rolling(window=14, min_periods=5).mean()
        sd = s.rolling(window=14, min_periods=5).std()
        return (s - m) / sd
    df["z_pct"] = df.groupby("symbol")["pct_change"].transform(zscore)
    df["is_outlier"] = df["z_pct"].abs() > 2.5
    return df
