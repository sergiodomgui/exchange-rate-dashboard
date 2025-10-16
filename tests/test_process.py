import pandas as pd
from src.process import add_derived_metrics, convert_base

# Datos de prueba base (USD/EUR, USD/GBP)
def _sample_df():
    return pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"] * 2),
        "base": ["USD"] * 6,
        "symbol": ["EUR"] * 3 + ["GBP"] * 3,
        "rate": [0.90, 0.91, 0.92, 0.80, 0.82, 0.81],
    })

def test_add_derived_metrics_basic():
    data = {
        "date": pd.date_range("2024-01-01", periods=10, freq="D").tolist() * 2,
        "base": ["USD"] * 20,
        "symbol": ["EUR"] * 10 + ["GBP"] * 10,
        "rate": list(range(10, 20)) + list(range(20, 30)),
    }
    df = pd.DataFrame(data)
    out = add_derived_metrics(df)
    # Se añade 'rsi14' a la verificación de columnas
    assert {"pct_change", "ma7", "std7", "z_pct", "is_outlier", "rsi14"}.issubset(set(out.columns))
    
    # El primer valor de pct_change por símbolo debe ser NaN
    first_rows = out.groupby("symbol").head(1)
    assert first_rows["pct_change"].isna().all()
    
    # El RSI debe ser NaN para las primeras 13 filas (ventana 14 - 1)
    assert out.groupby("symbol")["rsi14"].head(13).isna().all()

def test_convert_base_to_eur():
    df = _sample_df()
    # Conversión de USD/X a EUR/X
    # EUR (0.90) y GBP (0.80)
    # USD/EUR (2024-01-01) = 0.90
    # USD/GBP (2024-01-01) = 0.80
    # ---------------------------
    # EUR/USD debe ser 1/0.90 ≈ 1.111
    # EUR/GBP debe ser 0.80/0.90 ≈ 0.888

    out = convert_base(df, "EUR")

    # 1. Verificar la nueva base
    assert (out["base"] == "EUR").all()
    # 2. Verificar que el antiguo símbolo (EUR) se convierte en el antiguo base (USD)
    assert "USD" in out["symbol"].unique()
    assert "GBP" in out["symbol"].unique()
    assert "EUR" not in out["symbol"].unique()
    
    # 3. Verificar los valores de la nueva tasa (2024-01-01)
    # La tasa USD/EUR en esa fecha es 0.90
    eur_rate_original = df[(df["symbol"] == "EUR") & (df["date"] == "2024-01-01")]["rate"].iloc[0]
    
    # Tasa EUR/USD: 1 / 0.90
    rate_usd = out[(out["symbol"] == "USD") & (out["date"] == "2024-01-01")]["rate"].iloc[0]
    assert abs(rate_usd - (1.0 / eur_rate_original)) < 1e-3

    # Tasa EUR/GBP: (USD/GBP) / (USD/EUR) = 0.80 / 0.90
    rate_gbp_original = df[(df["symbol"] == "GBP") & (df["date"] == "2024-01-01")]["rate"].iloc[0]
    rate_gbp = out[(out["symbol"] == "GBP") & (out["date"] == "2024-01-01")]["rate"].iloc[0]
    assert abs(rate_gbp - (rate_gbp_original / eur_rate_original)) < 1e-3
    
def test_convert_base_no_change():
    df = _sample_df()
    base_original = df["base"].iloc[0]
    out = convert_base(df, base_original)
    
    # Si la base de destino es la misma que la base de origen, el DF debe ser idéntico
    pd.testing.assert_frame_equal(df.sort_values(["symbol", "date"]).reset_index(drop=True), out)