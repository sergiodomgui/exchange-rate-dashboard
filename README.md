**Exchange Rate Dashboard (Streamlit & Data Engineering)**

**Descripción breve:**
Dashboard interactivo y solución de *Data Engineering* que analiza y visualiza tipos de cambio históricos y en tiempo real, integrando indicadores financieros avanzados mediante una app web construida con **Streamlit**.

**Tecnologías principales:**
`Python`, `Streamlit`, `Plotly`, `pandas`, `requests`, `pytest`, `frankfurter.app API`

**Características destacadas:**

1. **Extracción y Caching de Datos**

   * Consumo de la API de *frankfurter.app* para obtener tasas históricas y actuales.
   * Limpieza y almacenamiento en CSV con caché local para optimizar rendimiento.

2. **Procesamiento y Métricas Financieras**

   * Cálculo de variación diaria, medias y desviaciones móviles (7 días) y RSI (14 días).
   * Detección de anomalías mediante *Z-score* y marcado de *outliers*.
   * Conversión dinámica de moneda base (e.g., USD → EUR).
   * Tests automatizados para validar la lógica de procesamiento.

3. **Dashboard Interactivo (Frontend)**

   * Visualizaciones avanzadas con **Plotly** (series temporales, outliers, RSI).
   * Mapa de calor de correlaciones entre divisas.
   * Consulta de tasas en tiempo real y estadísticas resumen.
   * Interfaz limpia y dinámica en **Streamlit**.
