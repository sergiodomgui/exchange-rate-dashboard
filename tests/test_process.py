import pandas as pd
from src.process import add_derived_metrics

def test_add_derived_metrics_basic():
    data = {
        "date": pd.date_range("2024-01-01", periods=10, freq="D").tolist() * 2,
        "base": ["USD"] * 20,
        "symbol": ["EUR"] * 10 + ["GBP"] * 10,
        "rate": list(range(10, 20)) + list(range(20, 30)),
    }
    df = pd.DataFrame(data)
    out = add_derived_metrics(df)
    assert {"pct_change", "ma7", "std7", "z_pct", "is_outlier"}.issubset(set(out.columns))
    # El primer valor de pct_change por símbolo debe ser NaN
    first_rows = out.groupby("symbol").head(1)
    assert first_rows["pct_change"].isna().all()
