import streamlit as st
import pandas as pd
from datetime import date, timedelta
from src.config import DEFAULT_BASE, DEFAULT_SYMBOLS
from src.fetch_rates import fetch_timeseries, cache_path_for
from src.process import tidy_rates, add_derived_metrics

st.set_page_config(page_title="Exchange Rate Dashboard", layout="wide")

st.title("💱 Exchange Rate Dashboard")
st.caption("API: exchangerate.host · pandas · Streamlit")

with st.sidebar:
    st.header("Ajustes")
    base = st.text_input("Moneda base", value=DEFAULT_BASE)
    symbols = st.text_input("Monedas (coma-separadas)", value=",".join(DEFAULT_SYMBOLS))
    days = st.slider("Días de historial", min_value=7, max_value=365, value=90)

    if st.button("Descargar/Actualizar datos"):
        end = date.today()
        start = end - timedelta(days=days)
        raw = fetch_timeseries(start.isoformat(), end.isoformat(), base=base, symbols=[s.strip() for s in symbols.split(",") if s.strip()])
        st.success(f"Datos descargados: {len(raw.get('rates', {}))} días")
        st.stop()

st.info("Para refrescar datos usa el botón en la barra lateral. El dashboard intenta leer el último CSV cacheado en data/.")

# Intentar leer el cache más reciente
try:
    latest_cache = cache_path_for()
    df = pd.read_csv(latest_cache, parse_dates=["date"])
except Exception:
    st.warning("No se encontró cache. Descarga datos desde la barra lateral para continuar.")
    st.stop()

symbols_available = sorted(df["symbol"].unique().tolist())
sel_symbols = st.multiselect("Monedas a visualizar", options=symbols_available, default=symbols_available[:4])

df_show = df[df["symbol"].isin(sel_symbols)].copy()
df_show = add_derived_metrics(df_show)

tab1, tab2, tab3 = st.tabs(["Serie (nivel)", "Variación diaria %", "Media móvil y outliers"])

with tab1:
    st.subheader("Serie de tipos de cambio")
    pivot = df_show.pivot(index="date", columns="symbol", values="rate")
    st.line_chart(pivot)

with tab2:
    st.subheader("Variación diaria (%)")
    pivot = df_show.pivot(index="date", columns="symbol", values="pct_change")
    st.line_chart(pivot)

with tab3:
    st.subheader("Media móvil (7d) y outliers (Z>2.5)")
    st.markdown("Los puntos con `is_outlier=True` indican cambios anómalos según un Z-score simple.")
    st.dataframe(df_show[df_show["is_outlier"]].sort_values(["symbol", "date"]).reset_index(drop=True))
