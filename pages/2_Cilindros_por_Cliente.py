import streamlit as st
import gspread
from google.oauth2 import service_account
import pandas as pd

# 1) Importamos la función de autenticación
from auth import check_password

# Primero verificamos la contraseña.
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
        sheet = client.open("TEST TRAZABILIDAD").worksheet(sheet_name)
        df = pd.DataFrame(sheet.get_all_records())
        df.columns = df.columns.str.strip().str.upper()  # Normalizar columnas
        return df
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return None

# ------------------------------------------------------------------
# Cargar datos
# ------------------------------------------------------------------
df_proceso = get_gsheet_data("PROCESO")
df_detalle = get_gsheet_data("DETALLE")

# ------------------------------------------------------------------
# Normalizar columna SERIE en df_detalle
# ------------------------------------------------------------------
if df_detalle is not None and "SERIE" in df_detalle.columns:
    df_detalle["SERIE"] = (
        df_detalle["SERIE"]
        .astype(str)
        .str.replace(",", "", regex=False)
    )

# ------------------------------------------------------------------
# UI
# ------------------------------------------------------------------
st.title("FASTRACK")
st.subheader("CONSULTA DE CILINDROS POR CLIENTE")

if df_proceso is not None:
    clientes_unicos = df_proceso["CLIENTE"].dropna().unique()
    cliente_seleccionado = st.selectbox("Seleccione el cliente:", clientes_unicos)
else:
    cliente_seleccionado = None

# ------------------------------------------------------------------
# Botón de búsqueda
# ------------------------------------------------------------------
if st.button("Buscar Cilindros del Cliente"):
    if cliente_seleccionado and df_proceso is not None and df_detalle is not None:
        # Merge con todas las columnas necesarias
        df_mov = df_detalle.merge(
            df_proceso[["IDPROC", "FECHA", "HORA", "PROCESO", "CLIENTE", "UBICACION"]],
            on="IDPROC",
            how="left"
        )

        # Asegurar columnas necesarias
        df_mov["SERIE"] = df_mov["SERIE"].astype(str).str.replace(",", "", regex=False)
        df_mov["FECHA"] = df_mov["FECHA"].astype(str)
        df_mov["HORA"] = df_mov["HORA"].astype(str)

        # Filtrar por cliente
        df_cliente = df_mov[df_mov["CLIENTE"] == cliente_seleccionado].copy()

        # Crear columna datetime para ordenamiento
        df_cliente["FECHA_HORA"] = pd.to_datetime(
            df_cliente["FECHA"] + " " + df_cliente["HORA"],
            format="%d/%m/%Y %H:%M",
            errors="coerce"
        )

        # Obtener el último movimiento por SERIE
        df_ultimos = (
            df_cliente
            .sort_values(by="FECHA_HORA", ascending=False)
            .drop_duplicates(subset="SERIE", keep="first")
        )

        # Filtrar solo procesos de entrega
        df_entregados = df_ultimos[df_ultimos["PROCESO"].isin(["DESPACHO", "ENTREGA"])]

        if not df_entregados.empty:
            st.success(f"Cilindros actualmente en el cliente: {cliente_seleccionado}")

            columnas_mostrar = ["SERIE", "IDPROC", "FECHA", "HORA", "PROCESO", "SERVICIO"]
            columnas_existentes = [col for col in columnas_mostrar if col in df_entregados.columns]

            st.dataframe(df_entregados[columnas_existentes])

            def convert_to_csv(df: pd.DataFrame) -> bytes:
                return df[columnas_existentes].to_csv(index=False).encode("utf-8")

            st.download_button(
                label="⬇️ Descargar resultados en CSV",
                data=convert_to_csv(df_entregados),
                file_name=f"cilindros_{cliente_seleccionado}.csv",
                mime="text/csv",
            )
        else:
            st.warning("No se encontraron cilindros actualmente en el cliente seleccionado.")
    else:
        st.warning("Por favor, seleccione un cliente.")
