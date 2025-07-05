import streamlit as st
import gspread
from google.oauth2 import service_account
import pandas as pd

# 1) Autenticación
from auth import check_password

if not check_password():
    st.stop()

# ------------------------------------------------------------------
# Función de carga desde Google Sheets
# ------------------------------------------------------------------
def get_gsheet_data(sheet_name: str) -> pd.DataFrame | None:
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=scopes
        )
        client = gspread.authorize(credentials)
        df = pd.DataFrame(
            client.open("TEST TRAZABILIDAD").worksheet(sheet_name).get_all_records()
        )
        df.columns = df.columns.str.strip().str.upper()
        return df
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return None

# ------------------------------------------------------------------
# Cargar datos
# ------------------------------------------------------------------
df_proceso  = get_gsheet_data("PROCESO")
df_detalle  = get_gsheet_data("DETALLE")

# ------------------------------------------------------------------
# LIMPIEZA:  quitar posibles columnas duplicadas en df_detalle
# ------------------------------------------------------------------
cols_dup = [c for c in ["PROCESO", "FECHA", "HORA", "CLIENTE", "UBICACION"] if c in df_detalle.columns]
if cols_dup:
    df_detalle = df_detalle.drop(columns=cols_dup)

# Normalizar SERIE
df_detalle["SERIE"] = df_detalle["SERIE"].astype(str).str.replace(",", "", regex=False)

# ------------------------------------------------------------------
# UI
# ------------------------------------------------------------------
st.title("FASTRACK")
st.subheader("CONSULTA DE CILINDROS POR CLIENTE")

clientes_unicos = df_proceso["CLIENTE"].dropna().unique()
cliente_seleccionado = st.selectbox("Seleccione el cliente:", clientes_unicos)

# ------------------------------------------------------------------
# Botón de búsqueda
# ------------------------------------------------------------------
if st.button("Buscar Cilindros del Cliente"):
    if cliente_seleccionado:
        # 1. Merge detalle + proceso (ya sin columnas duplicadas)
        df_mov = df_detalle.merge(
            df_proceso[["IDPROC", "FECHA", "HORA", "PROCESO", "CLIENTE", "UBICACION"]],
            on="IDPROC",
            how="left"
        )

        # 2. Filtrar por cliente
        df_cliente = df_mov[df_mov["CLIENTE"] == cliente_seleccionado].copy()

        # 3. FECHA_HORA para ordenar
        df_cliente["FECHA_HORA"] = pd.to_datetime(
            df_cliente["FECHA"] + " " + df_cliente["HORA"],
            format="%d/%m/%Y %H:%M",
            errors="coerce"
        )

        # 4. Último movimiento por SERIE
        df_ultimos = (
            df_cliente
            .sort_values("FECHA_HORA", ascending=False)
            .drop_duplicates("SERIE", keep="first")
        )

        # 5. Solo DESPACHO / ENTREGA  ⇒ cilindros aún en cliente
        df_entregados = df_ultimos[df_ultimos["PROCESO"].isin(["DESPACHO", "ENTREGA"])]

        # 6. Mostrar resultado
        if not df_entregados.empty:
            st.success(f"Cilindros actualmente en el cliente: {cliente_seleccionado}")

            columnas = ["SERIE", "IDPROC", "FECHA", "HORA", "PROCESO", "SERVICIO"]
            columnas = [c for c in columnas if c in df_entregados.columns]

            st.dataframe(df_entregados[columnas])

            st.download_button(
                "⬇️ Descargar resultados en CSV",
                data=df_entregados[columnas].to_csv(index=False).encode("utf-8"),
                file_name=f"cilindros_{cliente_seleccionado}.csv",
                mime="text/csv",
            )
        else:
            st.warning("No se encontraron cilindros actualmente en el cliente seleccionado.")
    else:
        st.warning("Por favor, seleccione un cliente.")
