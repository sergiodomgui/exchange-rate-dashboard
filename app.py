import streamlit as st
import pandas as pd
from datetime import date, timedelta
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from src.config import DEFAULT_BASE, DEFAULT_SYMBOLS
from src.fetch_rates import fetch_timeseries, cache_path_for, fetch_latest_rate
from src.process import tidy_rates, add_derived_metrics, convert_base

st.set_page_config(page_title="Exchange Rate Dashboard", layout="wide")

st.title("💱 Exchange Rate Dashboard")
st.caption("API: exchangerate.host · pandas · Streamlit")

with st.sidebar:
    st.header("Ajustes")
    
    # La moneda base de descarga se mantiene en DEFAULT_BASE
    base_download = st.text_input("Moneda base (Descarga API)", value=DEFAULT_BASE, disabled=True)
    symbols = st.text_input("Monedas (coma-separadas)", value=",".join(DEFAULT_SYMBOLS))
    days = st.slider("Días de historial", min_value=7, max_value=365, value=90)

    if st.button("Descargar/Actualizar datos"):
        end = date.today()
        start = end - timedelta(days=days)
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

# Sección de Conversión en Tiempo Real (asumiendo que ya fue añadida)
st.subheader("Conversión en Tiempo Real (Latest Rate)")
col_from, col_to, col_amount = st.columns(3)

all_currencies = sorted(list(df_show["symbol"].unique()) + [new_base])

with col_from:
    convert_from = st.selectbox("Convertir De", options=all_currencies, index=all_currencies.index(new_base))

with col_to:
    default_to_idx = 0 if len(all_currencies) == 1 else 1 
    convert_to = st.selectbox("Convertir A", options=all_currencies, index=default_to_idx)

with col_amount:
    amount = st.number_input("Cantidad", min_value=0.01, value=100.0, step=10.0)

if st.button(f"Calcular {convert_from} a {convert_to}"):
    st.markdown("---")
    if convert_from == convert_to:
        st.error("Las divisas de origen y destino no pueden ser las mismas.")
    else:
        latest_rate = fetch_latest_rate(base=convert_from, symbol=convert_to)
        
        if latest_rate is not None:
            result = amount * latest_rate
            st.success(f"**Tasa actual ({convert_from}/{convert_to}):** `{latest_rate:,.4f}`")
            st.metric(label=f"{amount:,.2f} {convert_from} es igual a", value=f"{result:,.2f} {convert_to}")
        else:
            st.warning(f"No fue posible obtener la tasa actual para {convert_from}/{convert_to}.")

st.markdown("---")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Serie (nivel) & Outliers", "Variación diaria %", "Media móvil & Outliers (Tabla)", "RSI (14d)", "Estadísticas Resumen", "Correlación"])

# --- TAB 1: Serie y Outliers (Plotly Avanzado) ---
with tab1:
    st.subheader(f"Serie de tipos de cambio (Base: {new_base})")
    
    fig = go.Figure()
    
    for symbol in sel_symbols:
        df_sym = df_show[df_show["symbol"] == symbol].copy()
        
        # 1. Trazar la línea principal
        fig.add_trace(go.Scatter(
            x=df_sym["date"], 
            y=df_sym["rate"], 
            mode='lines', 
            name=symbol
        ))
        
        # 2. Trazar los Outliers como puntos (círculos rojos)
        df_outliers = df_sym[df_sym["is_outlier"]]
        if not df_outliers.empty:
            fig.add_trace(go.Scatter(
                x=df_outliers["date"], 
                y=df_outliers["rate"], 
                mode='markers', 
                marker=dict(color='Red', size=8, symbol='circle'),
                name=f'{symbol} Outlier',
                hovertext=[
                    f"Fecha: {d.date()}<br>Tasa: {r:,.4f}<br>% Cambio: {pc:,.2f}% (Outlier)"
                    for d, r, pc in zip(df_outliers["date"], df_outliers["rate"], df_outliers["pct_change"])
                ],
                hoverinfo='text'
            ))

    fig.update_layout(
        title=f"Tipo de Cambio vs. {new_base}", 
        xaxis_title="Fecha", 
        yaxis_title="Tasa",
        hovermode="x unified",
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: Variación diaria % (Plotly) ---
with tab2:
    st.subheader("Variación diaria (%)")
    pivot = df_show.pivot(index="date", columns="symbol", values="pct_change").dropna()
    fig = px.line(pivot, x=pivot.index, y=pivot.columns, title="Variación Porcentual Diaria")
    fig.update_layout(yaxis_title="Variación (%)", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

# --- TAB 3: Media móvil y outliers (Tabla) ---
with tab3:
    st.subheader("Media móvil (7d) y outliers (Z>2.5)")
    st.markdown("Los puntos con `is_outlier=True` indican cambios anómalos según un Z-score simple.")
    st.dataframe(df_show[df_show["is_outlier"]].sort_values(["symbol", "date"]).reset_index(drop=True))

# --- TAB 4: RSI (14d) (Plotly) ---
with tab4:
    st.subheader("Relative Strength Index (RSI) a 14 días")
    st.markdown("El RSI ayuda a identificar si una divisa está **sobrecomprada (>70)** o **sobrevendida (<30)**.")
    pivot = df_show.pivot(index="date", columns="symbol", values="rsi14").dropna()
    
    fig = px.line(pivot, x=pivot.index, y=pivot.columns, title="RSI a 14 Días")
    
    # Añadir líneas horizontales de Sobrecompra (70) y Sobrevenda (30)
    fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Sobrecompra (70)", annotation_position="top right")
    fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Sobrevenda (30)", annotation_position="bottom right")
    
    fig.update_layout(yaxis_title="RSI", hovermode="x unified", yaxis_range=[0, 100])
    st.plotly_chart(fig, use_container_width=True)
    
# --- TAB 5: Estadísticas Resumen ---
with tab5:
    st.subheader("Estadísticas Descriptivas por Moneda")
    
    if not df_show.empty:
        # Calcular estadísticas
        summary_df = df_show.groupby("symbol").agg(
            **{
                "Última Tasa": ("rate", lambda x: f"{x.iloc[-1]:,.4f}"),
                "Máximo (Tasa)": ("rate", "max"),
                "Mínimo (Tasa)": ("rate", "min"),
                "Var. Diaria Última (%)": ("pct_change", lambda x: f"{x.iloc[-1]:,.2f}%"),
                "RSI Último": ("rsi14", lambda x: f"{x.iloc[-1]:,.2f}"),
                "Días Outlier": ("is_outlier", "sum"),
            }
        ).reset_index().rename(columns={"symbol": "Moneda"})
        
        # Aplicar formato decimal
        summary_df["Máximo (Tasa)"] = summary_df["Máximo (Tasa)"].apply(lambda x: f"{x:,.4f}")
        summary_df["Mínimo (Tasa)"] = summary_df["Mínimo (Tasa)"].apply(lambda x: f"{x:,.4f}")
        
        st.dataframe(summary_df.set_index("Moneda"))
    else:
        st.info("Selecciona monedas para ver las estadísticas.")

# --- TAB 6: Correlación (Mapa de Calor) ---
with tab6:
    st.subheader("Correlación de la Variación Diaria (%)")
    st.markdown("El mapa de calor muestra qué tan estrechamente se mueven las divisas (en porcentaje) entre sí.")
    
    # Calcular la matriz de correlación de la variación diaria
    pct_pivot = df_show.pivot(index="date", columns="symbol", values="pct_change").dropna()
    correlation_matrix = pct_pivot.corr()

    if not correlation_matrix.empty:
        # Crear el mapa de calor con Plotly
        fig = px.imshow(
            correlation_matrix,
            text_auto=True,
            aspect="auto",
            color_continuous_scale='RdBu_r', # Rojo-Azul (el rojo es negativo, azul es positivo)
            title=f"Matriz de Correlación de {new_base} Crosse-Rates"
        )
        fig.update_xaxes(side="top")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Se necesitan al menos dos monedas y suficientes datos para calcular la correlación.")