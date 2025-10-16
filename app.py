import streamlit as st
import pandas as pd
from datetime import date, timedelta
from src.config import DEFAULT_BASE, DEFAULT_SYMBOLS
from src.fetch_rates import fetch_timeseries, cache_path_for
from src.process import tidy_rates, add_derived_metrics, convert_base # Se importa convert_base
from src.fetch_rates import fetch_timeseries, cache_path_for, fetch_latest_rate # Añadir fetch_latest_rate

st.set_page_config(page_title="Exchange Rate Dashboard", layout="wide")

st.title("💱 Exchange Rate Dashboard")
st.caption("API: exchangerate.host · pandas · Streamlit")

with st.sidebar:
    st.header("Ajustes")
    
    # CAMBIO 1: Permitir la selección de una nueva base
    # La moneda base de descarga se mantiene en DEFAULT_BASE para la API, 
    # pero se puede cambiar la base de visualización.
    base_download = st.text_input("Moneda base (Descarga API)", value=DEFAULT_BASE, disabled=True)
    symbols = st.text_input("Monedas (coma-separadas)", value=",".join(DEFAULT_SYMBOLS))
    days = st.slider("Días de historial", min_value=7, max_value=365, value=90)

    if st.button("Descargar/Actualizar datos"):
        end = date.today()
        start = end - timedelta(days=days)
        # Usamos base_download, que es el DEFAULT_BASE, para la llamada a la API
        raw = fetch_timeseries(start.isoformat(), end.isoformat(), base=base_download, symbols=[s.strip() for s in symbols.split(",") if s.strip()])
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
base_original = df["base"].iloc[0]

# Selector de Moneda Base para Visualización
available_bases = [base_original] + symbols_available
new_base = st.selectbox("Cambiar moneda base de visualización", options=available_bases, index=0)

if new_base != base_original:
    df_processed = convert_base(df, new_base)
else:
    df_processed = df.copy()

symbols_available_processed = sorted(df_processed["symbol"].unique().tolist())
sel_symbols = st.multiselect("Monedas a visualizar", options=symbols_available_processed, default=symbols_available_processed[:4])

df_show = df_processed[df_processed["symbol"].isin(sel_symbols)].copy()
df_show = add_derived_metrics(df_show)

# ... (código existente de lectura de cache y preparación de df_show) ...

st.subheader("Conversión en Tiempo Real (Latest Rate)")
col_from, col_to, col_amount = st.columns(3)

# Obtener divisas disponibles del cache y añadir la base actual (new_base)
all_currencies = sorted(list(df_show["symbol"].unique()) + [new_base])

with col_from:
    # Divisa FROM (la que tienes)
    convert_from = st.selectbox("Convertir De", options=all_currencies, index=all_currencies.index(new_base))

with col_to:
    # Divisa TO (la que quieres)
    # Selecciona la segunda divisa de la lista como predeterminada (si existe)
    default_to_idx = 0 if len(all_currencies) == 1 else 1 
    convert_to = st.selectbox("Convertir A", options=all_currencies, index=default_to_idx)

with col_amount:
    amount = st.number_input("Cantidad", min_value=0.01, value=100.0, step=10.0)

if st.button(f"Calcular {convert_from} a {convert_to}"):
    st.markdown("---")
    if convert_from == convert_to:
        st.error("Las divisas de origen y destino no pueden ser las mismas.")
    else:
        # Llamada a la nueva función de la API
        latest_rate = fetch_latest_rate(base=convert_from, symbol=convert_to)
        
        if latest_rate is not None:
            result = amount * latest_rate
            st.success(f"**Tasa actual ({convert_from}/{convert_to}):** `{latest_rate:,.4f}`")
            st.metric(label=f"{amount:,.2f} {convert_from} es igual a", value=f"{result:,.2f} {convert_to}")
        else:
            st.warning(f"No fue posible obtener la tasa actual para {convert_from}/{convert_to}.")

# CAMBIO 3: Nueva pestaña para RSI
tab1, tab2, tab3, tab4 = st.tabs(["Serie (nivel)", "Variación diaria %", "Media móvil y outliers", "RSI (14d)"])

with tab1:
    st.subheader(f"Serie de tipos de cambio (Base: {new_base})")
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

with tab4:
    # CAMBIO 4: Visualización del RSI
    st.subheader("Relative Strength Index (RSI) a 14 días")
    st.markdown("El RSI ayuda a identificar si una divisa está sobrecomprada (>70) o sobrevendida (<30).")
    pivot = df_show.pivot(index="date", columns="symbol", values="rsi14")
    st.line_chart(pivot)