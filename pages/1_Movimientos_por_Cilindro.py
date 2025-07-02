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
        sheet = client.open("TRAZABILIDAD").worksheet(sheet_name)
        return pd.DataFrame(sheet.get_all_records())
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return None

# ------------------------------------------------------------------
# Cargar datos
# ------------------------------------------------------------------
df_proceso = get_gsheet_data("PROCESO")
df_detalle = get_gsheet_data("DETALLE")

# Normalizar columna SERIE en df_detalle
if df_detalle is not None:
    df_detalle["SERIE"] = (
        df_detalle["SERIE"]
        .astype(str)
        .str.replace(",", "", regex=False)
    )

# ------------------------------------------------------------------
# UI
# ------------------------------------------------------------------
st.title("FASTRACK")
st.subheader("CONSULTA DE MOVIMIENTOS POR CILINDRO")

target_cylinder = st.text_input("Ingrese la ID del cilindro a buscar:")

if st.button("Buscar"):
    if target_cylinder:
        # Limpiamos el input
        target_cylinder_normalized = target_cylinder.replace(",", "")

        # 1) Filtrar df_detalle para este cilindro
        df_det_for_cyl = df_detalle.loc[
            df_detalle["SERIE"] == target_cylinder_normalized,
            ["IDPROC", "SERIE", "SERVICIO"]
        ]

        # 2) Filtrar procesos cuyo IDPROC esté en esa lista
        df_proc_for_cyl = df_proceso[
            df_proceso["IDPROC"].isin(df_det_for_cyl["IDPROC"])
        ]

        if df_proc_for_cyl.empty:
            st.warning("No se encontraron movimientos para el cilindro ingresado.")
        else:
            # 3) Hacemos merge para unir información de proceso + servicio
            df_resultados = df_proc_for_cyl.merge(
                df_det_for_cyl,
                on="IDPROC",
                how="left"
            )

            st.success(f"Movimientos para el cilindro ID {target_cylinder}:")
            st.dataframe(
                df_resultados[
                    ["FECHA", "HORA", "IDPROC", "PROCESO", "CLIENTE", "UBICACION", "SERIE", "SERVICIO"]
                ]
            )

            # ------------------------------------------------------------------
            # Función compacta para convertir a CSV y luego a bytes
            # ------------------------------------------------------------------
            def convert_to_csv(dataframe: pd.DataFrame) -> bytes:
                return dataframe.to_csv(index=False).encode("utf-8")

            st.download_button(
                label="⬇️ Descargar resultados en CSV",
                data=convert_to_csv(df_resultados),
                file_name=f"movimientos_{target_cylinder}.csv",
                mime="text/csv",
            )
    else:
        st.warning("Por favor, ingrese una ID de cilindro.")
