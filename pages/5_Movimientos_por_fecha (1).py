import streamlit as st
import gspread
from google.oauth2 import service_account
import pandas as pd
from datetime import datetime, timedelta

from auth import check_password

# ————————————————————————————————
# 1) Autenticación
# ————————————————————————————————
if not check_password():
    st.stop()

# ————————————————————————————————
# 2) Función para cargar cada hoja
# ————————————————————————————————
def get_gsheet_data(sheet_name: str) -> pd.DataFrame | None:
    try:
        creds = st.secrets["gcp_service_account"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials = service_account.Credentials.from_service_account_info(
            creds, scopes=scopes
        )
        client = gspread.authorize(credentials)
        sheet = client.open("TRAZABILIDAD").worksheet(sheet_name)
        df = pd.DataFrame(sheet.get_all_records())
        # Normalizar nombres de columnas
        df.columns = df.columns.str.strip().str.upper()
        return df
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return None

# ————————————————————————————————
# 3) Cargar datos
# ————————————————————————————————
df_proceso = get_gsheet_data("PROCESO")
df_detalle = get_gsheet_data("DETALLE")

# ————————————————————————————————
# 4) Limpiar SERIE y asegurar texto
# ————————————————————————————————
if df_detalle is not None and "SERIE" in df_detalle.columns:
    df_detalle["SERIE"] = (
        df_detalle["SERIE"]
        .astype(str)
        .str.replace(",", "", regex=False)
    )

# ————————————————————————————————
# 5) Convertir FECHA a datetime en df_proceso
# ————————————————————————————————
if df_proceso is not None and "FECHA" in df_proceso.columns:
    df_proceso["FECHA"] = pd.to_datetime(
        df_proceso["FECHA"], format="%d/%m/%Y", errors="coerce"
    )

# ————————————————————————————————
# 6) UI: rango de fechas
# ————————————————————————————————
st.title("FASTRACK")
st.subheader("CONSULTA DE MOVIMIENTOS POR RANGO DE FECHA")

today = datetime.now().date()
default_range = (today - timedelta(days=7), today)

start_date, end_date = st.date_input(
    "Seleccione rango de fechas",
    value=default_range,
    help="Elija fecha de inicio y fecha de término"
)

# ————————————————————————————————
# 7) Al hacer clic en Buscar
# ————————————————————————————————
if st.button("Buscar"):
    # Validar que los DataFrames estén cargados
    if df_proceso is None or df_detalle is None:
        st.error("No se pudieron cargar los datos de Google Sheets.")
    # Validar rango
    elif start_date > end_date:
        st.warning("La fecha de inicio no puede ser posterior a la fecha de término.")
    else:
        # 1) Filtrar procesos por fecha (parte date)
        mask = (
            (df_proceso["FECHA"].dt.date >= start_date)
            & (df_proceso["FECHA"].dt.date <= end_date)
        )
        df_proc_filtered = df_proceso.loc[mask]

        if df_proc_filtered.empty:
            st.warning("No se encontraron movimientos en ese rango de fechas.")
        else:
            # 2) Merge con df_detalle para traer SERIE y SERVICIO (uno a muchos)
            df_merged = df_proc_filtered.merge(
                df_detalle[["IDPROC", "SERIE", "SERVICIO"]],
                on="IDPROC",
                how="left"
            )

            # 3) Convertir FECHA a date puro
            df_merged["FECHA"] = df_merged["FECHA"].dt.date

            # 4) Mostrar resultados
            st.success(
                f"Movimientos desde {start_date.isoformat()} hasta {end_date.isoformat()}:"
            )
            st.dataframe(
                df_merged[
                    ["FECHA", "IDPROC", "PROCESO", "CLIENTE", "UBICACION", "SERIE", "SERVICIO"]
                ]
            )

            # 5) Botón de descarga CSV
            def convert_to_csv(df: pd.DataFrame) -> bytes:
                return df.to_csv(index=False).encode("utf-8")

            filename = f"movimientos_{start_date.isoformat()}_a_{end_date.isoformat()}.csv"
            st.download_button(
                label="⬇️ Descargar resultados",
                data=convert_to_csv(df_merged),
                file_name=filename,
                mime="text/csv",
            )
