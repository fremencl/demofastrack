import streamlit as st
import gspread
from google.oauth2 import service_account
import pandas as pd

# 1) Importamos la función de autenticación
from auth import check_password

# Primero verificamos la contraseña.
if not check_password():
    st.stop()

# Función para obtener datos desde Google Sheets
def get_gsheet_data(sheet_name):
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=scopes
        )
        client = gspread.authorize(credentials)
        sheet = client.open("TRAZABILIDAD").worksheet(sheet_name)
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return None

# Cargar los datos
df_proceso = get_gsheet_data("PROCESO")
df_detalle = get_gsheet_data("DETALLE")

# Normalizar columnas
df_proceso.columns = df_proceso.columns.str.strip().str.upper()
df_detalle.columns = df_detalle.columns.str.strip().str.upper()

# Convertir claves a texto
df_proceso["IDPROC"] = df_proceso["IDPROC"].astype(str)
df_detalle["IDPROC"] = df_detalle["IDPROC"].astype(str)

# Eliminar columna PROCESO de df_detalle si existe
if "PROCESO" in df_detalle.columns:
    df_detalle = df_detalle.drop(columns=["PROCESO"])

# Merge conservando campos principales
df_movimientos = df_detalle.merge(
    df_proceso[["IDPROC", "PROCESO", "FECHA", "CLIENTE", "UBICACION"]],
    on="IDPROC",
    how="left"
)

# Título y subtítulo
st.title("FASTRACK")
st.subheader("Último Movimiento de Cada Cilindro")

# Normalización de serie
df_movimientos["SERIE"] = df_movimientos["SERIE"].astype(str).str.replace(",", "", regex=False)

# Conversión de fecha
df_movimientos["FECHA"] = pd.to_datetime(df_movimientos["FECHA"], format="%d/%m/%Y", errors="coerce")

# Primero preparamos solo la lista de ubicaciones (sin procesar toda la data aún)
ubicaciones = df_movimientos["UBICACION"].dropna().unique().tolist()
ubicacion_seleccionada = st.selectbox("Selecciona una ubicación:", ["Seleccionar..."] + ubicaciones)

# Si el usuario ha seleccionado una ubicación válida
if ubicacion_seleccionada != "Seleccionar...":
    # Filtrar por ubicación
    df_filtrado = df_movimientos[df_movimientos["UBICACION"] == ubicacion_seleccionada]

    # Obtener último movimiento por SERIE solo en el subset filtrado
    df_ultimo_movimiento = (
        df_filtrado
        .sort_values(by=["FECHA"], ascending=False)
        .drop_duplicates(subset="SERIE", keep="first")
    )

    if not df_ultimo_movimiento.empty:
        st.write(f"Últimos movimientos para ubicación: {ubicacion_seleccionada}")

        df_ultimo_movimiento["FECHA"] = df_ultimo_movimiento["FECHA"].dt.strftime("%Y-%m-%d")

        st.dataframe(df_ultimo_movimiento[["SERIE", "IDPROC", "FECHA", "PROCESO", "CLIENTE", "SERVICIO", "UBICACION"]])

        def convert_to_excel(dataframe):
            return dataframe.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Descargar listado en Excel",
            data=convert_to_excel(df_ultimo_movimiento),
            file_name=f"Ultimo_Movimiento_{ubicacion_seleccionada}.csv",
            mime="text/csv",
        )
    else:
        st.warning("No se encontraron movimientos para la ubicación seleccionada.")
else:
    st.info("Por favor, selecciona una ubicación para ver los resultados.")
