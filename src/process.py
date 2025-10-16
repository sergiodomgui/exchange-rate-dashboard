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

def convert_base(df: pd.DataFrame, new_base: str) -> pd.DataFrame:
    """Convierte todos los tipos de cambio a una nueva base (currency).

    Asume que el DataFrame original tiene la columna 'base' y 'rate' (ej: USD/EUR = 0.9).
    La nueva base debe ser una de las divisas en la columna 'symbol'.

    Ejemplo: si la base original es USD, y la nueva base es EUR:
    La tasa EUR/X se calcula como (USD/X) / (USD/EUR).
    """
    if df.empty:
        return df
    
    # 1. Obtener la tasa de la nueva base respecto a la base original (new_base / original_base)
    # Por ejemplo, si original_base=USD y new_base=EUR, necesitamos la tasa USD/EUR.
    base_rate_df = df[(df['symbol'] == new_base) & (df['base'].iloc[0] != new_base)]
    
    if base_rate_df.empty:
        # La nueva base es la base actual o no existe en los símbolos. No hay conversión posible.
        if df['base'].iloc[0] == new_base:
            return df.copy()
        
        # En caso de que se intente convertir a un símbolo que no está en el dataset,
        # lanzamos un error o devolvemos el original para simplicidad, pero con advertencia.
        print(f"Advertencia: La divisa '{new_base}' no se encontró como símbolo para la conversión de base.")
        return df.copy()

    # Preparar el DataFrame resultante
    df_new = df.copy()
    
    # 2. Pivotear las tasas de la nueva base para unir por fecha
    # La tasa es (Original_Base / New_Base). Ejemplo: USD/EUR.
    base_rate_pivot = base_rate_df.pivot(index='date', columns='symbol', values='rate').rename(columns={new_base: 'new_base_rate'})
    
    # 3. Unir la tasa pivotada con el DataFrame completo (por fecha)
    df_new = df_new.merge(base_rate_pivot, left_on='date', right_index=True, how='left')
    
    # 4. Calcular la nueva tasa: New_Rate = Old_Rate / (Original_Base / New_Base)
    # (Original_Base / Symbol) / (Original_Base / New_Base) = (New_Base / Symbol)
    df_new['rate'] = np.where(
        df_new['symbol'] == new_base,  # Si el símbolo es la nueva base, la tasa es 1.0
        1.0, 
        df_new['rate'] / df_new['new_base_rate']
    )
    
    # 5. Actualizar las columnas 'base' y 'symbol' (para el antiguo new_base)
    df_new['base'] = new_base
    df_new.loc[df_new['symbol'] == new_base, 'symbol'] = df['base'].iloc[0] # El antiguo base se convierte en simbolo (ej: USD)
    
    # Limpiar columnas temporales y devolver
    return df_new.drop(columns=['new_base_rate']).sort_values(["symbol", "date"]).reset_index(drop=True)

def _rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """Calcula el Relative Strength Index (RSI) para una serie."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # El cálculo de la media móvil exponencial (EMA) para el RSI usa la
    # fórmula de Wilder: alpha = 1 / window.
    avg_gain = gain.ewm(com=window - 1, min_periods=window).mean()
    avg_loss = loss.ewm(com=window - 1, min_periods=window).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def add_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["symbol", "date"]).copy()
    
    # 1. Variación diaria por símbolo
    df["pct_change"] = df.groupby("symbol")["rate"].pct_change() * 100.0
    
    # 2. Media móvil 7 días y desviación
    df["ma7"] = df.groupby("symbol")["rate"].transform(lambda s: s.rolling(window=7, min_periods=3).mean())
    df["std7"] = df.groupby("symbol")["rate"].transform(lambda s: s.rolling(window=7, min_periods=3).std())
    
    # 3. Z-score simple sobre pct_change
    def zscore(s: pd.Series) -> pd.Series:
        m = s.rolling(window=14, min_periods=5).mean()
        sd = s.rolling(window=14, min_periods=5).std()
        return (s - m) / sd
    df["z_pct"] = df.groupby("symbol")["pct_change"].transform(zscore)
    df["is_outlier"] = df["z_pct"].abs() > 2.5
    
    # 4. NUEVO: Relative Strength Index (RSI) - Ventana 14 días
    df["rsi14"] = df.groupby("symbol")["rate"].transform(lambda s: _rsi(s, window=14))
    
    return df