import streamlit as st
import gspread
from google.oauth2 import service_account
import pandas as pd
from datetime import datetime, timedelta

from auth import check_password

if not check_password():
    st.stop()

def get_gsheet_data(sheet_name):
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
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

# Cargar ambas hojas
df_proceso = get_gsheet_data("PROCESO")
df_detalle = get_gsheet_data("DETALLE")

# Normalizar nombres de columnas
df_proceso.columns = df_proceso.columns.str.strip().str.upper()
df_detalle.columns = df_detalle.columns.str.strip().str.upper()

# Asegurar que IDPROC es string
df_proceso["IDPROC"] = df_proceso["IDPROC"].astype(str)
df_detalle["IDPROC"] = df_detalle["IDPROC"].astype(str)

# Si existiera, quitamos la columna PROCESO de df_detalle
if "PROCESO" in df_detalle.columns:
    df_detalle = df_detalle.drop(columns=["PROCESO"])

# ——— Aquí estaba el error: no existe SERVICIO en df_proceso ———
# Conservamos SERVICIO de df_detalle y traemos PROCESO/FECHA/CLIENTE desde df_proceso
df_movimientos = df_detalle.merge(
    df_proceso[["IDPROC", "PROCESO", "FECHA", "CLIENTE"]],
    on="IDPROC",
    how="left"
)

st.title("FASTRACK")
st.subheader("CILINDROS NO RETORNADOS")

# Limpiar y convertir fechas
df_movimientos["SERIE"] = (
    df_movimientos["SERIE"]
    .astype(str)
    .str.replace(",", "", regex=False)
)
df_movimientos["FECHA"] = pd.to_datetime(
    df_movimientos["FECHA"], format="%d/%m/%Y", errors="coerce"
)

# Filtrar entregas >30 días
fecha_limite = datetime.now() - timedelta(days=30)
df_entregados = df_movimientos[
    (df_movimientos["PROCESO"].isin(["DESPACHO", "ENTREGA"])) &
    (df_movimientos["FECHA"] < fecha_limite)
]
df_entregados_ultimo = (
    df_entregados
    .sort_values(by="FECHA", ascending=False)
    .drop_duplicates(subset="SERIE", keep="first")
)

# Últimos retornos
df_retorno = df_movimientos[df_movimientos["PROCESO"].isin(["RETIRO", "RECEPCION"])]
df_retorno_ultimo = (
    df_retorno
    .sort_values(by="FECHA", ascending=False)
    .drop_duplicates(subset="SERIE", keep="first")
)

# Detectar cuáles no han retorno posterior a la entrega
df_retorno_validos = df_retorno_ultimo.merge(
    df_entregados_ultimo[["SERIE", "FECHA"]],
    on="SERIE",
    suffixes=("_retorno", "_entrega")
)
df_retorno_validos = df_retorno_validos[
    df_retorno_validos["FECHA_retorno"] > df_retorno_validos["FECHA_entrega"]
]

entregados_set = set(df_entregados_ultimo["SERIE"])
retornados_set = set(df_retorno_validos["SERIE"])
no_retorno = entregados_set - retornados_set

df_no_retorno = df_entregados_ultimo[
    df_entregados_ultimo["SERIE"].isin(no_retorno)
]

if not df_no_retorno.empty:
    st.write("Cilindros entregados hace más de 30 días y no retornados:")

    df_no_retorno["FECHA"] = df_no_retorno["FECHA"].dt.strftime("%Y-%m-%d")

    # Ahora sí existe SERVICIO en el DataFrame
    st.dataframe(
        df_no_retorno[["SERIE", "IDPROC", "FECHA", "PROCESO", "CLIENTE", "SERVICIO"]]
    )

    def convert_to_csv(df: pd.DataFrame) -> bytes:
        return df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Descargar listado en Excel",
        data=convert_to_csv(df_no_retorno),
        file_name="Cilindros_No_Retornados.csv",
        mime="text/csv",
    )
else:
    st.warning("No se encontraron cilindros entregados hace más de 30 días y no retornados.")
